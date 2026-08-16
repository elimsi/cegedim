// src/validators.js
// n8n Code Node for validating Bordereau rows (Enriched Schema - Option B)

console.log("Starting validators node...");

if (!items || !items.length || !items[0].json || !items[0].json.rows) {
    console.log("Error: No valid rows provided from parser");
    return [{ json: { error: "No input data" } }];
}

const inputData = items[0].json;
const rows = inputData.rows;

// Regex patterns based on CLAUDE.md
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

// 1. Validate each line individually and collect rejected PS (Contagion logic)
const psRejetMap = {}; // Maps num_ps to the first raison_rejet found

for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const ps = row.num_ps;
    
    // If PS is already marked as rejected (contagion), we can skip further deep validation
    if (psRejetMap[ps]) continue;

    // A. Presence checks (all 13 fields must be non-empty)
    const requiredFields = [
        'num_ps', 'email', 'bic', 'iban', 'intitule', 'montant', 
        'date_vir', 'numvir', 'code_acte', 'specialite', 'region', 
        'date_soin', 'nb_actes'
    ];
    
    let missingField = null;
    for (const field of requiredFields) {
        if (!row[field] || row[field].trim() === "") {
            missingField = field;
            break;
        }
    }
    
    if (missingField) {
        psRejetMap[ps] = `CHAMP_MANQUANT_${missingField.toUpperCase()}`;
        console.log(`PS ${ps} rejected: CHAMP_MANQUANT_${missingField.toUpperCase()}`);
        continue;
    }

    // B. Format Checks
    if (!REGEX.num_ps.test(row.num_ps)) {
        psRejetMap[ps] = "FORMAT_NUM_PS";
        continue;
    }
    if (!REGEX.email.test(row.email)) {
        psRejetMap[ps] = "FORMAT_EMAIL";
        continue;
    }
    if (!REGEX.montant.test(row.montant)) {
        psRejetMap[ps] = "FORMAT_MONTANT";
        continue;
    }
    if (!REGEX.date_vir.test(row.date_vir)) {
        psRejetMap[ps] = "FORMAT_DATE_VIR";
        continue;
    }
    if (!REGEX.date_soin.test(row.date_soin)) {
        psRejetMap[ps] = "FORMAT_DATE_SOIN";
        continue;
    }
    if (!REGEX.numvir.test(row.numvir)) {
        psRejetMap[ps] = "FORMAT_NUMVIR";
        continue;
    }
    if (!REGEX.nb_actes.test(row.nb_actes)) {
        psRejetMap[ps] = "FORMAT_NB_ACTES";
        continue;
    }
    if (!VALID_CODE_ACTE.includes(row.code_acte)) {
        psRejetMap[ps] = "CODE_ACTE_INVALIDE";
        continue;
    }
}

// 2. Separate into rows_valides and rows_rejetees (Enforce Contagion Rule)
const rows_valides = [];
const rows_rejetees = [];
const ps_valides_set = new Set();

for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const ps = row.num_ps;
    
    if (psRejetMap[ps]) {
        // Reject this line with the contagion reason
        row.raison_rejet = psRejetMap[ps];
        rows_rejetees.push(row);
    } else {
        // Keep as valid
        rows_valides.push(row);
        ps_valides_set.add(ps);
    }
}

const ps_rejetes = Object.keys(psRejetMap);
const ps_valides = Array.from(ps_valides_set);

console.log(`Validation complete:`);
console.log(`- ${rows_valides.length} lignes valides (${ps_valides.length} PS)`);
console.log(`- ${rows_rejetees.length} lignes rejetées (${ps_rejetes.length} PS)`);

// Return exactly one n8n item with the structured results
return [{
    json: {
        rows_valides: rows_valides,
        rows_rejetees: rows_rejetees,
        ps_valides: ps_valides,
        ps_rejetes: ps_rejetes,
        nb_lignes_valides: rows_valides.length,
        nb_lignes_rejetees: rows_rejetees.length,
        has_rejets: rows_rejetees.length > 0,
        email_emetteur: inputData.email_emetteur,
        fichier_source: inputData.fichier_source
    }
}];
