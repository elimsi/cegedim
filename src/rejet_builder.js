// src/rejet_builder.js
// n8n Code Node for building the CSV of rejected rows

console.log("Starting rejet_builder node...");

if (!items || !items.length || !items[0].json) {
    console.log("Error: No input data provided");
    return [{ json: { error: "No input data" } }];
}

// Read rows_rejetees from input
const rows_rejetees = items[0].json.rows_rejetees || [];

// The 13 Enriched Columns + RAISON_REJET
const headers = [
    "NUM_PS", "EMAIL", "BIC", "IBAN", "INTITULE", "MONTANT", "DATE_VIR",
    "NUMVIR", "CODE_ACTE", "SPECIALITE", "REGION", "DATE_SOIN",
    "NB_ACTES", "RAISON_REJET"
];

// Helper to escape fields for proper CSV format
function escapeCSV(field) {
    if (field === null || field === undefined) return "";
    const str = String(field);
    // If field contains comma, quote, or newline, wrap in quotes and escape quotes
    if (str.includes(",") || str.includes("\"") || str.includes("\n")) {
        return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
}

const csvLines = [];

// 1. Add header
csvLines.push(headers.join(","));

// 2. Add data rows
for (const row of rows_rejetees) {
    const line = [
        escapeCSV(row.num_ps),
        escapeCSV(row.email),
        escapeCSV(row.bic),
        escapeCSV(row.iban),
        escapeCSV(row.intitule),
        escapeCSV(row.montant),
        escapeCSV(row.date_vir),
        escapeCSV(row.numvir),
        escapeCSV(row.code_acte),
        escapeCSV(row.specialite),
        escapeCSV(row.region),
        escapeCSV(row.date_soin),
        escapeCSV(row.nb_actes),
        escapeCSV(row.raison_rejet) // The reason from validators.js
    ];
    csvLines.push(line.join(","));
}

// 3. Add summary row at the end
csvLines.push(`TOTAL_REJETS,${rows_rejetees.length}`);

// Combine into single text body
const csv_content = csvLines.join("\n");

console.log(`Generated CSV with ${rows_rejetees.length} rejected rows.`);

return [{
    json: {
        csv_content: csv_content,
        nb_rejets: rows_rejetees.length
    }
}];
