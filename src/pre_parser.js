// src/pre_parser.js
// CETIP - Phase 3: Deterministic Pre-Parser
// Extracts raw rows from the bordereau file using regex + pipe splitting.
// FAST, 0-cost, and deterministic. Feeds structured data to the LLM for semantic validation.

console.log("[PreParser] Starting deterministic pre-parse...");

if (!items || !items.length || !items[0].json || !items[0].json.fileContent) {
    console.log("[PreParser] ERROR: Missing fileContent");
    return [{ json: { error: "No file content", rows_parsed: [], total_lignes: 0 } }];
}

const fileContent = items[0].json.fileContent;
const fileName = items[0].json.fileName || "bordereau.ok";
const db_ids = items[0].json.db_ids || [];
const lines = fileContent.split(/\r?\n/);

let emailEmetteur = null;
let dateFichier = null;
let compteEmetteur = null;
const rows_parsed = [];

for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Extract header metadata
    if (line.includes("MAIL EMETTEUR :")) {
        const m = line.match(/MAIL EMETTEUR\s*:\s*([^\|\s]+)/i);
        if (m) emailEmetteur = m[1].trim();
        continue;
    }
    if (line.includes("VIREMENTS") && line.includes("LE")) {
        const mDate = line.match(/LE\s+(\d{2}\/\d{2}\/\d{4})/);
        if (mDate) dateFichier = mDate[1].trim();
        const mCompte = line.match(/COMPTE EMETTEUR\s*:\s*(\S+)/i);
        if (mCompte) compteEmetteur = mCompte[1].trim();
        continue;
    }
    if (line.startsWith("+") || line.includes("N°PS") || line.includes("N° PROF")) continue;

    // Parse data row
    if (line.startsWith("|")) {
        const content = line.substring(1, line.endsWith("|") ? line.length - 1 : line.length);
        const cols = content.split("|").map(c => c.trim());
        if (cols.length >= 13) {
            rows_parsed.push({
                num_ps: cols[0],
                email: cols[1],
                bic: cols[2],
                iban: cols[3],
                intitule: cols[4],
                montant: cols[5],
                date_vir: cols[6],
                numvir: cols[7],
                code_acte: cols[8],
                specialite: cols[9],
                region: cols[10],
                date_soin: cols[11],
                nb_actes: cols[12]
            });
        }
    }
}

console.log(`[PreParser] Extracted ${rows_parsed.length} rows from ${fileName}`);

return [{
    json: {
        rows_parsed,
        email_emetteur: emailEmetteur || "unknown@cetip.fr",
        date_fichier: dateFichier || "INCONNU",
        compte_emetteur: compteEmetteur || "INCONNU",
        total_lignes: rows_parsed.length,
        fichier_source: fileName,
        db_ids
    }
}];
