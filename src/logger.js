// src/logger.js
// n8n Code Node for building SQL inserts into the Kimball Data Warehouse (PostgreSQL)

console.log("Starting logger node...");

if (!items || !items.length || !items[0].json) {
    console.log("Error: No input data provided");
    return [{ json: { error: "No input data" } }];
}

const inputData = items[0].json;
const rows_valides = inputData.rows_valides || [];
const rows_rejetees = inputData.rows_rejetees || [];
const fichier_source = inputData.fichier_source || "unknown_file";

// Utility to safely wrap strings for SQL injection prevention within n8n generated queries
function safeString(val) {
    if (val === null || val === undefined || val === '') return 'NULL';
    // Escape single quotes by doubling them (standard SQL)
    const escaped = String(val).replace(/'/g, "''");
    return `'${escaped}'`;
}

// Utility to safely parse numeric amounts from French format ("999,99")
function safeNum(val) {
    if (val === null || val === undefined || val === '') return 'NULL';
    if (typeof val === 'string') {
        const parsed = parseFloat(val.replace(',', '.'));
        if (isNaN(parsed)) return 'NULL';
        return parsed;
    }
    return val;
}

// Convert "YYYYMMDD" or "SSAAMMJJ" (e.g. "20260805") to INTEGER
function dateToId(val) {
    if (!val || val.trim() === '' || val.length !== 8) return 'NULL';
    const parsed = parseInt(val, 10);
    if (isNaN(parsed)) return 'NULL';
    return parsed;
}

let sqlInserts = "";
const insertedPs = new Set();
const insertedDates = new Set();
let totalQueries = 0;

// Issue 11: Defensively ensure dim_date rows exist before FK insert
function ensureDateExists(dateId) {
    if (dateId === 'NULL' || insertedDates.has(dateId)) return;
    const d = String(dateId);
    if (d.length !== 8) return;
    const year = parseInt(d.substring(0, 4));
    const month = parseInt(d.substring(4, 6));
    const day = parseInt(d.substring(6, 8));
    const quarter = Math.ceil(month / 3);
    // ISO week approximation (good enough for PoC)
    const dt = new Date(year, month - 1, day);
    const startOfYear = new Date(year, 0, 1);
    const week = Math.ceil(((dt - startOfYear) / 86400000 + startOfYear.getDay() + 1) / 7);
    
    sqlInserts += `\nINSERT INTO dim_date (date_id, jour, mois, trimestre, annee, semaine) VALUES (${dateId}, ${day}, ${month}, ${quarter}, ${year}, ${week}) ON CONFLICT (date_id) DO NOTHING;\n`;
    insertedDates.add(dateId);
    totalQueries++;
}

function processRows(rows, statut) {
    for (const row of rows) {
        // 1. Insert Dimension PS if not already inserted in this batch
        if (!insertedPs.has(row.num_ps)) {
            const sqlPs = `
INSERT INTO dim_ps (num_ps, email, intitule, specialite, region, bic, iban)
VALUES (
    ${safeString(row.num_ps)}, 
    ${safeString(row.email)}, 
    ${safeString(row.intitule)}, 
    ${safeString(row.specialite)}, 
    ${safeString(row.region)}, 
    ${safeString(row.bic)}, 
    ${safeString(row.iban)}
) ON CONFLICT (num_ps) DO NOTHING;`;
            sqlInserts += sqlPs + "\n";
            insertedPs.add(row.num_ps);
            totalQueries++;
        }

        // 2. Insert Fact Traitement
        // Ensure date dimensions exist (Issue 11: prevent FK violations)
        const dateVirId = dateToId(row.date_vir);
        const dateSoinId = dateToId(row.date_soin);
        ensureDateExists(dateVirId);
        ensureDateExists(dateSoinId);
        
        // If ML layer was called, these fields might be present in valid rows. For rejected, they are NULL.
        const flag_anomalie = (statut === 'VALIDE') ? safeString(row.flag_anomalie) : 'NULL';
        const score_anomalie = (statut === 'VALIDE') ? safeNum(row.score_anomalie) : 'NULL';
        const montant_moyen = (statut === 'VALIDE') ? safeNum(row.montant_moyen_historique_ps) : 'NULL';
        const ecart = (statut === 'VALIDE') ? safeNum(row.ecart_vs_historique) : 'NULL';
        const raison_rejet = (statut === 'REJETE') ? safeString(row.raison_rejet) : 'NULL';

        const sqlFact = `
INSERT INTO fact_traitements (
    date_execution, date_vir_id, date_soin_id, num_ps, code_acte, num_virement, 
    montant, nb_actes, statut, raison_rejet, flag_anomalie, score_anomalie, 
    montant_moyen_historique_ps, ecart_vs_historique, fichier_source
) VALUES (
    NOW(),
    ${dateVirId},
    ${dateSoinId},
    ${safeString(row.num_ps)},
    ${safeString(row.code_acte)},
    ${safeString(row.numvir)},
    ${safeNum(row.montant)},
    ${safeNum(row.nb_actes)},
    '${statut}',
    ${raison_rejet},
    ${flag_anomalie},
    ${score_anomalie},
    ${montant_moyen},
    ${ecart},
    ${safeString(fichier_source)}
);`;
        sqlInserts += sqlFact + "\n";
        totalQueries++;
    }
}

// Process both valid and rejected rows
processRows(rows_valides, 'VALIDE');
processRows(rows_rejetees, 'REJETE');

console.log(`Generated ${totalQueries} SQL statements for logging.`);

return [{
    json: {
        sql_inserts: sqlInserts,
        summary: {
            rows_valides_logged: rows_valides.length,
            rows_rejetees_logged: rows_rejetees.length,
            unique_ps_synced: insertedPs.size,
            total_queries: totalQueries
        }
    }
}];
