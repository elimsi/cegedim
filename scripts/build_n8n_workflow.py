import json
from pathlib import Path

def read_src(filename):
    path = Path(f"src/{filename}")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"// {filename} not found"

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"

LLM_SYSTEM_PROMPT = (
    "Tu es un expert en validation de bordereaux de virement CETIP (Cegedim). "
    "Analyse les lignes JSON fournies et retourne UNIQUEMENT un tableau JSON (sans markdown). "
    "Chaque objet du tableau doit contenir :\\n"
    "- is_valid (boolean)\\n"
    "- raison_rejet (string | null) : code court en MAJUSCULES si invalide (ex: FORMAT_MONTANT, INCOHERENCE_CODE_ACTE)\\n"
    "- anomalie_semantique (string | null) : incohérence métier détectée même si le format est valide\\n"
    "  Ex: 'KINESITHERAPEUTE avec code CS (réservé aux médecins)', 'Montant 45000 EUR inhabituel pour un acte AIS d'INFIRMIER'\\n"
    "- correction_suggeree (string | null) : correction triviale si possible\\n\\n"
    "Règles CETIP strictes:\\n"
    "- MONTANT : format NNNNNN,CC (virgule française, 1-6 chiffres avant, 2 après)\\n"
    "- CODE_ACTE valides UNIQUEMENT : C, CS, V, AIS, AMK, AMI, BSB\\n"
    "- Cohérence code_acte <-> specialite :\\n"
    "  * C / CS -> MEDECIN_GENERALISTE ou CARDIOLOGUE\\n"
    "  * AIS / AMI -> INFIRMIER\\n"
    "  * AMK -> KINESITHERAPEUTE\\n"
    "  * BSB -> PHARMACIEN\\n"
    "- IBAN : 27 caractères commençant par FR\\n"
    "- NUM_PS : 9 chiffres\\n"
    "- EMAIL : format valide avec @ et domaine\\n"
    "Retourne autant d'objets que de lignes en entrée, dans le meme ordre."
)


def build_workflow():
    nodes = []
    connections = {}

    def add_node(node_id, name, type_name, position, params=None, typeVersion=1):
        if params is None:
            params = {}
        nodes.append({
            "id": node_id,
            "name": name,
            "type": type_name,
            "typeVersion": typeVersion,
            "position": position,
            "parameters": params
        })

    def add_conn(from_node, to_node, out_index=0, in_index=0):
        if from_node not in connections:
            connections[from_node] = {"main": [[]]}
        while len(connections[from_node]["main"]) <= out_index:
            connections[from_node]["main"].append([])
        connections[from_node]["main"][out_index].append({
            "node": to_node,
            "type": "main",
            "index": in_index
        })

    # =========================================================
    # 1. TRIGGER — Schedule (every 5 minutes, fully automated)
    # =========================================================
    add_node("node-trigger", "Schedule Trigger", "n8n-nodes-base.scheduleTrigger", [180, 480], {
        "rule": {
            "interval": [{"field": "cronExpression", "expression": "*/5 * * * *"}]
        }
    }, 1.2)

    # =========================================================
    # 2. FETCH PENDING FILES FROM DB
    # =========================================================
    fetch_query = (
        "UPDATE bordereaux_inbox "
        "SET statut = 'EN_COURS', date_traitement = NOW() "
        "WHERE id IN ("
        "  SELECT id FROM bordereaux_inbox "
        "  WHERE statut = 'EN_ATTENTE' "
        "  ORDER BY id ASC LIMIT 10"
        ") RETURNING *;"
    )
    add_node("node-fetch-db", "Fetch Pending Files", "n8n-nodes-base.postgres", [400, 480], {
        "operation": "executeQuery",
        "query": fetch_query
    }, 2.5)
    add_conn("Schedule Trigger", "Fetch Pending Files")

    # Guard: if no files found, stop silently
    add_node("node-check-files", "Files Found?", "n8n-nodes-base.if", [600, 480], {
        "conditions": {
            "number": [{"value1": "={{ $items().length }}", "operation": "larger", "value2": 0}]
        }
    })
    add_conn("Fetch Pending Files", "Files Found?")

    # =========================================================
    # 3. MERGE FILE CONTENTS
    # =========================================================
    merge_code = (
        "if (!items || items.length === 0) return [];\n"
        "let mergedContent = '';\n"
        "const ids = [];\n"
        "for (const item of items) {\n"
        "  mergedContent += item.json.contenu + '\\n';\n"
        "  ids.push(item.json.id);\n"
        "}\n"
        "return [{ json: {\n"
        "  fileContent: mergedContent,\n"
        "  fileName: 'batch_db_' + ids.join('_') + '.ok',\n"
        "  db_ids: ids\n"
        "}}];"
    )
    add_node("node-merge", "Merge Files", "n8n-nodes-base.code", [820, 480], {
        "jsCode": merge_code
    }, 2)
    add_conn("Files Found?", "Merge Files", out_index=0)  # True branch

    # =========================================================
    # 4. PRE-PARSER (deterministic JS extraction)
    # =========================================================
    add_node("node-preparser", "Pre-Parser", "n8n-nodes-base.code", [1040, 480], {
        "jsCode": read_src("pre_parser.js")
    }, 2)
    add_conn("Merge Files", "Pre-Parser")

    # =========================================================
    # 5. LLM SEMANTIC VALIDATOR (Mistral AI)
    # =========================================================
    llm_body = (
        "={\n"
        "  \"model\": \"" + MISTRAL_MODEL + "\",\n"
        "  \"messages\": [\n"
        "    { \"role\": \"system\", \"content\": " + json.dumps(LLM_SYSTEM_PROMPT) + " },\n"
        "    { \"role\": \"user\", \"content\": {{ JSON.stringify($json.rows_parsed) | json }} }\n"
        "  ],\n"
        "  \"temperature\": 0.1,\n"
        "  \"response_format\": { \"type\": \"json_object\" }\n"
        "}"
    )
    add_node("node-llm", "LLM Semantic Validator (Mistral)", "n8n-nodes-base.httpRequest", [1260, 480], {
        "method": "POST",
        "url": MISTRAL_API_URL,
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "Authorization", "value": "=Bearer {{ $env.MISTRAL_API_KEY }}"},
                {"name": "Content-Type", "value": "application/json"}
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": llm_body
    }, 4.2)
    add_conn("Pre-Parser", "LLM Semantic Validator (Mistral)")

    # =========================================================
    # 6. POST-LLM GUARD-RAIL VALIDATOR
    # =========================================================
    add_node("node-postvalidator", "Post-LLM Validator", "n8n-nodes-base.code", [1480, 480], {
        "jsCode": read_src("post_llm_validator.js")
    }, 2)
    add_conn("LLM Semantic Validator (Mistral)", "Post-LLM Validator")

    # =========================================================
    # 7. ROUTE: REJECTIONS BRANCH
    # =========================================================
    add_node("node-if", "Has Rejections?", "n8n-nodes-base.if", [1700, 480], {
        "conditions": {"boolean": [{"value1": "={{ $json.has_rejets }}", "value2": True}]}
    })
    add_conn("Post-LLM Validator", "Has Rejections?")

    # Rejection flow
    add_node("node-rejet", "Rejet Builder", "n8n-nodes-base.code", [1920, 280], {
        "jsCode": read_src("rejet_builder.js")
    }, 2)
    add_conn("Has Rejections?", "Rejet Builder", out_index=0)

    add_node("node-email-emetteur", "Email Emetteur", "n8n-nodes-base.emailSend", [2140, 280], {
        "fromEmail": "cetip@cegedim.com",
        "toEmail": "={{ $json.email_destinataire }}",
        "subject": "={{ $json.sujet_email }}",
        "text": "Anomalies detectees. Voir piece jointe.",
        "attachments": "data"
    }, 2)
    add_conn("Rejet Builder", "Email Emetteur")

    # =========================================================
    # 8. VALID FLOW — GROUP + LOOP PER PS
    # =========================================================
    add_node("node-grouper", "Grouper", "n8n-nodes-base.code", [1920, 620], {
        "jsCode": read_src("grouper.js")
    }, 2)
    add_conn("Has Rejections?", "Grouper", out_index=1)  # False branch

    add_node("node-split", "SplitInBatches", "n8n-nodes-base.splitInBatches", [2140, 620], {
        "batchSize": 1
    }, 3)
    add_conn("Grouper", "SplitInBatches")

    # =========================================================
    # 9. ML SCORING (Isolation Forest FastAPI)
    # =========================================================
    ml_body = (
        "={\n"
        "  \"num_ps\": \"{{ $json.num_ps }}\",\n"
        "  \"email\": \"{{ $json.email }}\",\n"
        "  \"intitule\": \"{{ $json.intitule }}\",\n"
        "  \"specialite\": \"{{ $json.specialite }}\",\n"
        "  \"region\": \"{{ $json.region }}\",\n"
        "  \"bic\": \"{{ $json.bic }}\",\n"
        "  \"iban\": \"{{ $json.iban }}\",\n"
        "  \"montant\": {{ $json.montant_total }},\n"
        "  \"nb_actes\": {{ $json.nb_actes_total }},\n"
        "  \"montant_par_acte\": {{ $json.montant_moyen_par_acte }}\n"
        "}"
    )
    add_node("node-ml", "FastAPI ML (Isolation Forest)", "n8n-nodes-base.httpRequest", [2360, 620], {
        "method": "POST",
        "url": "http://fastapi:8000/predict-anomaly",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": ml_body
    }, 4.1)
    add_conn("SplitInBatches", "FastAPI ML (Isolation Forest)", out_index=1)

    # =========================================================
    # 10. TEMPLATE FILLER (merge ML data + HTML template)
    # =========================================================
    template_html = read_src("pdf_template.html")
    tf_wrapper = (
        "// Inject ML results and HTML template\n"
        "const ps = $('SplitInBatches').first().json;\n"
        "const ml = items[0].json;\n"
        "ps.flag_anomalie = ml.flag_anomalie;\n"
        "ps.score_anomalie = ml.score_anomalie;\n"
        "ps.template_html = `" + template_html.replace("`", "\\`") + "`;\n"
        "items[0].json = ps;\n"
        "\n"
        + read_src("template_filler.js")
    )
    add_node("node-template", "Template Filler", "n8n-nodes-base.code", [2580, 620], {
        "jsCode": tf_wrapper
    }, 2)
    add_conn("FastAPI ML (Isolation Forest)", "Template Filler")

    # =========================================================
    # 11. GOTENBERG (HTML → PDF)
    # =========================================================
    html_to_bin = (
        "const html = items[0].json.filled_html;\n"
        "items[0].binary = {\n"
        "  data: {\n"
        "    data: Buffer.from(html, 'utf-8').toString('base64'),\n"
        "    mimeType: 'text/html',\n"
        "    fileName: 'index.html'\n"
        "  }\n"
        "};\n"
        "return items;"
    )
    add_node("node-html-bin", "Prepare Gotenberg", "n8n-nodes-base.code", [2800, 760], {
        "jsCode": html_to_bin
    }, 2)
    add_conn("Template Filler", "Prepare Gotenberg")

    add_node("node-gotenberg", "Gotenberg (PDF)", "n8n-nodes-base.httpRequest", [2800, 620], {
        "method": "POST",
        "url": "http://gotenberg:3000/forms/chromium/convert/html",
        "sendBinaryData": True,
        "binaryPropertyName": "data:files"
    }, 4.1)
    add_conn("Prepare Gotenberg", "Gotenberg (PDF)")

    # =========================================================
    # 12. EMAIL PS (Mailtrap SMTP)
    # =========================================================
    add_node("node-email-ps", "Email PS", "n8n-nodes-base.emailSend", [3020, 620], {
        "fromEmail": "virements@cegedim.com",
        "toEmail": "={{ $('SplitInBatches').first().json.email }}",
        "subject": "Votre Bordereau de Virement CETIP",
        "text": "Veuillez trouver votre bordereau de virement en piece jointe.",
        "attachments": "data"
    }, 2)
    add_conn("Gotenberg (PDF)", "Email PS")

    # =========================================================
    # 13. INSERT INTO BRONZE (raw data warehouse layer)
    # =========================================================
    bronze_insert = (
        "INSERT INTO bronze_bordereaux ("
        "num_ps, email, intitule, specialite, region, bic, iban, "
        "montant, nb_actes, code_acte, date_vir, date_soin, numvir, "
        "flag_anomalie, score_anomalie, fichier_source, date_ingestion"
        ") VALUES ("
        "'{{ $json.num_ps }}', '{{ $json.email }}', '{{ $json.intitule }}', "
        "'{{ $json.specialite }}', '{{ $json.region }}', '{{ $json.bic }}', '{{ $json.iban }}', "
        "{{ $json.montant_total }}, {{ $json.nb_actes_total }}, '{{ $json.code_acte }}', "
        "'{{ $json.date_vir }}', '{{ $json.date_soin }}', '{{ $json.numvir }}', "
        "'{{ $json.flag_anomalie }}', {{ $json.score_anomalie }}, "
        "'{{ $('Pre-Parser').item.json.fichier_source }}', NOW()"
        ") ON CONFLICT DO NOTHING;"
    )
    add_node("node-bronze", "Insert Bronze", "n8n-nodes-base.postgres", [3240, 620], {
        "operation": "executeQuery",
        "query": bronze_insert
    }, 2.5)
    add_conn("Email PS", "Insert Bronze")

    # =========================================================
    # 14. TRIGGER DBT RUN (Silver + Gold transformation)
    # =========================================================
    add_node("node-dbt", "dbt Run (Silver+Gold)", "n8n-nodes-base.httpRequest", [3460, 620], {
        "method": "POST",
        "url": "http://dbt-runner:8080/run",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={ \"models\": \"silver_traitements gold_fact_traitements\" }"
    }, 4.2)
    add_conn("Insert Bronze", "dbt Run (Silver+Gold)")

    # Loop back to SplitInBatches for next PS
    add_conn("dbt Run (Silver+Gold)", "SplitInBatches")

    # =========================================================
    # 15. MARK FILES AS TRAITE (after all batches done)
    # =========================================================
    # SplitInBatches done branch (out_index=0) → Mark files as TRAITE
    mark_done_query = (
        "UPDATE bordereaux_inbox "
        "SET statut = 'TRAITE', date_traitement = NOW() "
        "WHERE id = ANY(ARRAY[{{ $('Pre-Parser').item.json.db_ids.join(',') }}]::int[]);"
    )
    add_node("node-mark-done", "Mark Files TRAITE", "n8n-nodes-base.postgres", [2360, 480], {
        "operation": "executeQuery",
        "query": mark_done_query
    }, 2.5)
    add_conn("SplitInBatches", "Mark Files TRAITE", out_index=0)  # Done branch

    workflow = {
        "name": "CETIP - V3 Pipeline Enterprise (LLM + Medallion)",
        "nodes": nodes,
        "connections": connections,
        "settings": {
            "executionOrder": "v1"
        }
    }

    Path("n8n").mkdir(exist_ok=True)
    with open("n8n/workflow_export.json", "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    build_workflow()
    print("n8n/workflow_export.json successfully generated!")
