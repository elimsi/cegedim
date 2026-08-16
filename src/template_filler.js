// src/template_filler.js
// n8n Code Node — Replaces {{placeholders}} in pdf_template.html with real PS data.
// This node runs BETWEEN the Grouper output and the Gotenberg HTTP Request.
// Input: one item per PS from SplitInBatches (output of grouper.js)

console.log("Starting template_filler node...");

const ps = items[0].json;

// Read the HTML template from the mounted volume or from a stored string
// In n8n, this would be loaded via a Read File node or stored as a static string.
// For this Code node, we assume the template HTML is passed in as ps.template_html
// or we reconstruct it inline. In practice, use a "Read Binary File" node before this one.

let html = ps.template_html || '';

if (!html) {
    console.log("Warning: No template_html provided. Using fallback inline template.");
    // The n8n workflow should pipe the template via a Read File node.
    // This is a safety fallback.
    return [{ json: { error: "template_html not provided in input" } }];
}

// Format montant_total as "XX XXX,XX" (French financial format)
function formatMontant(num) {
    if (num === null || num === undefined) return '0,00';
    const parts = Number(num).toFixed(2).split('.');
    const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return intPart + ',' + parts[1];
}

// Format date_generation
const now = new Date();
const dateGeneration = now.toLocaleDateString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
});

// Replace simple placeholders
html = html.replace(/\{\{intitule\}\}/g, ps.intitule || '');
html = html.replace(/\{\{num_ps\}\}/g, ps.num_ps || '');
html = html.replace(/\{\{specialite\}\}/g, ps.specialite || '');
html = html.replace(/\{\{region\}\}/g, ps.region || '');
html = html.replace(/\{\{montant_total\}\}/g, formatMontant(ps.montant_total));
html = html.replace(/\{\{nb_actes_total\}\}/g, String(ps.nb_actes_total || 0));
html = html.replace(/\{\{date_generation\}\}/g, dateGeneration);

// Replace {{#each lignes}} ... {{/each}} loop
const eachRegex = /\{\{#each lignes\}\}([\s\S]*?)\{\{\/each\}\}/;
const match = html.match(eachRegex);

if (match && ps.lignes && ps.lignes.length > 0) {
    const rowTemplate = match[1];
    let rowsHtml = '';

    for (const ligne of ps.lignes) {
        let row = rowTemplate;
        row = row.replace(/\{\{numvir\}\}/g, ligne.numvir || '');
        row = row.replace(/\{\{code_acte\}\}/g, ligne.code_acte || '');
        row = row.replace(/\{\{date_soin\}\}/g, ligne.date_soin || '');
        row = row.replace(/\{\{nb_actes\}\}/g, String(ligne.nb_actes || 0));
        row = row.replace(/\{\{montant\}\}/g, ligne.montant || '0,00');
        rowsHtml += row;
    }

    html = html.replace(eachRegex, rowsHtml);
}

console.log(`Template filled for PS ${ps.num_ps} (${ps.lignes ? ps.lignes.length : 0} lines).`);

ps.filled_html = html;
ps.filename = `bordereau_${ps.num_ps}_${now.toISOString().slice(0,10)}.pdf`;

return [{
    json: ps
}];

