// src/post_llm_validator.js
// CETIP - Phase 3: Post-LLM Guard-Rail Validator
// Receives the LLM JSON response, parses decisions, and applies a deterministic fallback.
// The LLM provides semantic understanding; this code enforces structural safety.

console.log("[PostLLMValidator] Starting guard-rail validation...");

const inputData = items[0].json;

// --- 1. Parse LLM Response ---
let llm_decisions = [];

try {
    // The LLM HTTP response body is in items[0].json (n8n HTTP Request node output)
    // We expect an array of objects matching rows_parsed
    const llmBody = inputData.body || inputData;
    
    // Try to extract JSON from the LLM's response (it may wrap it in markdown ```json blocks)
    let rawText = "";
    if (llmBody.choices && llmBody.choices[0]) {
        rawText = llmBody.choices[0].message.content;
    } else if (typeof llmBody === "string") {
        rawText = llmBody;
    } else if (llmBody.outputs) {
        rawText = llmBody.outputs[0].text || "";
    }

    // Strip markdown code fences if present
    const jsonMatch = rawText.match(/```(?:json)?\s*([\s\S]*?)```/) || [null, rawText];
    llm_decisions = JSON.parse(jsonMatch[1].trim());
    console.log(`[PostLLMValidator] LLM returned ${llm_decisions.length} decisions.`);
} catch (e) {
    console.log(`[PostLLMValidator] WARNING: Failed to parse LLM response (${e.message}). Falling back to deterministic validation.`);
    llm_decisions = [];
}

// --- 2. Deterministic Fallback Regex (safety net if LLM fails/hallucinates) ---
const REGEX = {
    montant: /^\d{1,6},\d{2}$/,
    date_vir: /^\d{8}$/,
    date_soin: /^\d{8}$/,
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    num_ps: /^\d+$/,
    numvir: /^\d+$/,
    nb_actes: /^\d+$/
};
const VALID_CODE_ACTE = ['C', 'CS', 'V', 'AIS', 'AMK', 'AMI', 'BSB'];

// Retrieve the original rows from the pre-parser (passed via n8n workflow static data or input)
// We must get rows_parsed from a previous node. In n8n, use $('PreParser').item.json
let rows_parsed = [];
try {
    // Access pre-parser data from the workflow's execution data
    rows_parsed = $('Pre-Parser').item.json.rows_parsed || [];
} catch(e) {
    console.log("[PostLLMValidator] Could not access Pre-Parser data via $() shorthand. Using fallback.");
    rows_parsed = inputData.rows_parsed || [];
}

const meta = {
    email_emetteur: inputData.email_emetteur || "unknown@cetip.fr",
    date_fichier: inputData.date_fichier || "INCONNU",
    fichier_source: inputData.fichier_source || "unknown",
    db_ids: inputData.db_ids || []
};

// --- 3. Apply decisions row by row ---
const rows_valides = [];
const rows_rejetees = [];
const psRejetMap = {};

for (let i = 0; i < rows_parsed.length; i++) {
    const row = rows_parsed[i];
    const ps = row.num_ps;
    const llm = llm_decisions[i] || {};

    // Contagion: if PS already rejected, reject all its lines
    if (psRejetMap[ps]) {
        row.raison_rejet = psRejetMap[ps];
        row.llm_decision = "CONTAGION";
        rows_rejetees.push(row);
        continue;
    }

    let raison = null;
    let anomalie_semantique = llm.anomalie_semantique || null;

    // A. If LLM says invalid, trust it
    if (llm.is_valid === false) {
        raison = llm.raison_rejet || "REJET_LLM";
    }

    // B. Deterministic fallback (always run as safety net)
    if (!raison) {
        const required = ['num_ps','email','bic','iban','intitule','montant','date_vir','numvir','code_acte','specialite','region','date_soin','nb_actes'];
        for (const f of required) {
            if (!row[f] || row[f].trim() === "") { raison = `CHAMP_MANQUANT_${f.toUpperCase()}`; break; }
        }
    }
    if (!raison && !REGEX.montant.test(row.montant)) raison = "FORMAT_MONTANT";
    if (!raison && !REGEX.email.test(row.email)) raison = "FORMAT_EMAIL";
    if (!raison && !REGEX.num_ps.test(row.num_ps)) raison = "FORMAT_NUM_PS";
    if (!raison && !REGEX.date_vir.test(row.date_vir)) raison = "FORMAT_DATE_VIR";
    if (!raison && !REGEX.date_soin.test(row.date_soin)) raison = "FORMAT_DATE_SOIN";
    if (!raison && !VALID_CODE_ACTE.includes(row.code_acte)) raison = "CODE_ACTE_INVALIDE";

    if (raison) {
        psRejetMap[ps] = raison;
        row.raison_rejet = raison;
        row.llm_decision = llm.is_valid === false ? "LLM_REJECT" : "REGEX_REJECT";
        rows_rejetees.push(row);
    } else {
        // Valid row — attach LLM enrichments
        row.anomalie_semantique = anomalie_semantique;
        row.correction_suggeree = llm.correction_suggeree || null;
        row.llm_decision = "VALID";
        rows_valides.push(row);
    }
}

const ps_valides = [...new Set(rows_valides.map(r => r.num_ps))];
const ps_rejetes = Object.keys(psRejetMap);

console.log(`[PostLLMValidator] Validation complete:`);
console.log(`  - ${rows_valides.length} valid rows (${ps_valides.length} PS)`);
console.log(`  - ${rows_rejetees.length} rejected rows (${ps_rejetes.length} PS)`);
console.log(`  - ${rows_valides.filter(r => r.anomalie_semantique).length} semantic anomalies flagged by LLM`);

return [{
    json: {
        rows_valides,
        rows_rejetees,
        ps_valides,
        ps_rejetes,
        nb_lignes_valides: rows_valides.length,
        nb_lignes_rejetees: rows_rejetees.length,
        has_rejets: rows_rejetees.length > 0,
        ...meta
    }
}];
