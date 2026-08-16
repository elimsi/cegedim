// src/parser.js
// n8n Code Node for parsing Bordereau files (Enriched Schema - Option B)

console.log("Starting parser node...");

if (!items || !items.length || !items[0].json || !items[0].json.fileContent) {
    console.log("Error: Missing fileContent in input item");
    return [{
        json: {
            error: "No file content provided",
            rows: [],
            total_lignes: 0,
            fichier_source: "unknown"
        }
    }];
}

const fileContent = items[0].json.fileContent;
// Get filename if it exists, otherwise default
const fileName = items[0].json.fileName || "bordereau_virements.txt";

console.log(`Parsing file: ${fileName}`);

// 1. Split file into lines (handling both \n and \r\n)
const lines = fileContent.split(/\r?\n/);
console.log(`File has ${lines.length} total lines.`);

let emailEmetteur = null;
let dateFichier = null;
const parsedRows = [];

for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip empty lines
    if (!line) continue;
    
    // 2. Extract email_emetteur
    if (line.includes("MAIL EMETTEUR :")) {
        // Regex to match email after the colon
        const emailMatch = line.match(/MAIL EMETTEUR\s*:\s*([^\|\s]+)/i);
        if (emailMatch && emailMatch[1]) {
            emailEmetteur = emailMatch[1].trim();
            console.log(`Found email_emetteur: ${emailEmetteur}`);
        }
        continue;
    }
    
    // 3. Extract date_fichier
    if (line.includes("VIREMENTS") && line.includes("LE")) {
        // Match the date after 'LE '
        const dateMatch = line.match(/LE\s+(\d{2}\/\d{2}\/\d{4})/);
        if (dateMatch && dateMatch[1]) {
            dateFichier = dateMatch[1].trim();
            console.log(`Found date_fichier: ${dateFichier}`);
        }
        continue;
    }
    
    // 4. Skip separator lines
    if (line.startsWith("+")) {
        continue;
    }
    
    // 5. Skip header lines
    if (line.includes("N°PS") || line.includes("N° PROF")) {
        continue;
    }
    
    // 6. Process data lines
    if (line.startsWith("|")) {
        // Remove the leading pipe, and the trailing pipe if it exists
        const content = line.substring(1, line.length - (line.endsWith("|") ? 1 : 0));
        
        // Split by pipe and trim all values
        const columns = content.split("|").map(col => col.trim());
        
        // Ensure we have the correct number of columns (13 for Enriched Schema B)
        // N°PS | EMAIL | BIC | IBAN | INTITULE | MONTANT | DATE_VIR | NUMVIR | CODE_ACTE | SPECIALITE | REGION | DATE_SOIN | NB_ACTES
        if (columns.length >= 13) {
            parsedRows.push({
                num_ps: columns[0],
                email: columns[1],
                bic: columns[2],
                iban: columns[3],
                intitule: columns[4],
                montant: columns[5],
                date_vir: columns[6],
                numvir: columns[7],
                code_acte: columns[8],
                specialite: columns[9],
                region: columns[10],
                date_soin: columns[11],
                nb_actes: columns[12]
            });
        } else {
            console.log(`Warning: Line ${i + 1} has insufficient columns (${columns.length}): ${line}`);
        }
    }
}

console.log(`Successfully parsed ${parsedRows.length} data rows.`);

// Handle edge cases
if (parsedRows.length === 0) {
    console.log("Warning: No data rows found in the file.");
}

// Return single n8n item format
return [{
    json: {
        rows: parsedRows,
        email_emetteur: emailEmetteur || "unknown@example.com",
        date_fichier: dateFichier || "UNKNOWN_DATE",
        total_lignes: parsedRows.length,
        fichier_source: fileName
    }
}];
