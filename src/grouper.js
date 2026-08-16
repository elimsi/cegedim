// src/grouper.js
// n8n Code Node for grouping valid Bordereau rows by Professionnel de Santé (PS)

console.log("Starting grouper node...");

if (!items || !items.length || !items[0].json || !items[0].json.rows_valides) {
    console.log("Error: No valid rows provided from validators");
    return [{ json: { error: "No valid rows" } }];
}

const rowsValides = items[0].json.rows_valides;
const psGroups = {};

console.log(`Processing ${rowsValides.length} valid rows for grouping.`);

for (let i = 0; i < rowsValides.length; i++) {
    const row = rowsValides[i];
    const ps = row.num_ps;

    // Initialize group if it doesn't exist
    if (!psGroups[ps]) {
        psGroups[ps] = {
            num_ps: ps,
            email: row.email,
            intitule: row.intitule,
            specialite: row.specialite,
            region: row.region,
            bic: row.bic,
            iban: row.iban,
            lignes: [],
            montant_total: 0,
            nb_actes_total: 0,
            codes_actes_set: new Set()
        };
    }

    // Add row to group's lines — with derived montant_par_acte per line (Issue 8: ML needs per-line value)
    const montantParsed = parseFloat(row.montant.replace(',', '.'));
    const nbActesParsed = parseInt(row.nb_actes, 10);
    const montantParActe = nbActesParsed > 0 ? Math.round((montantParsed / nbActesParsed) * 100) / 100 : montantParsed;
    
    row.montant_par_acte = montantParActe;
    psGroups[ps].lignes.push(row);
    
    // Accumulate group totals
    psGroups[ps].montant_total += montantParsed;
    psGroups[ps].nb_actes_total += nbActesParsed;
    
    // Track unique code_acte
    if (row.code_acte) {
        psGroups[ps].codes_actes_set.add(row.code_acte);
    }
}

const resultItems = [];

for (const ps in psGroups) {
    const group = psGroups[ps];
    
    // Fix JS floating point precision issues (e.g. 25324.180000000004 -> 25324.18)
    const montantTotalRounded = Math.round(group.montant_total * 100) / 100;
    
    // Calculate average amount per act
    let montantMoyenParActe = 0;
    if (group.nb_actes_total > 0) {
        montantMoyenParActe = Math.round((montantTotalRounded / group.nb_actes_total) * 100) / 100;
    }

    resultItems.push({
        json: {
            num_ps: group.num_ps,
            email: group.email,
            intitule: group.intitule,
            specialite: group.specialite,
            region: group.region,
            bic: group.bic,
            iban: group.iban,
            montant_total: montantTotalRounded,
            nb_actes_total: group.nb_actes_total,
            montant_moyen_par_acte: montantMoyenParActe,
            nb_lignes: group.lignes.length,
            codes_actes_uniques: Array.from(group.codes_actes_set),
            lignes: group.lignes
        }
    });
}

console.log(`Grouped into ${resultItems.length} unique PS items.`);

// Return one item per PS. This feeds directly into n8n's Split In Batches node perfectly.
return resultItems;
