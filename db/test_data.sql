-- ============================================================================
-- CETIP Test Data — Realistic bordereaux for n8n workflow testing
-- ============================================================================

-- Clean previous data
TRUNCATE bordereaux_inbox RESTART IDENTITY CASCADE;
TRUNCATE bronze_bordereaux RESTART IDENTITY CASCADE;

-- ============================================================================
-- BORDEREAU 1: Fichier 100% valide — 5 PS, données propres
-- Scénario: Flux normal d'une mutuelle (MGEN)
-- ============================================================================
INSERT INTO bordereaux_inbox (nom_fichier, contenu, statut) VALUES (
'SEPA_VIREMENT_MGEN_20260815_001.ok',
'| VIREMENTS  COMPTE EMETTEUR : CC987654 FR76300010001234567890128 LE 15/08/2026 |
| MAIL EMETTEUR : tresorerie@mgen.fr |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| N°PS | EMAIL | BIC | IBAN | INTITULE | MONTANT | DATE_VIR | NUMVIR | CODE_ACTE | SPECIALITE | REGION | DATE_SOIN | NB_ACTES |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 111111111 | dr.dupont@cabinet-medical.fr | BNPAFRPP | FR7630001007941234567890185 | DR DUPONT JEAN-PIERRE | 253,00 | 20260815 | 4401 | C | MEDECIN_GENERALISTE | ILE_DE_FRANCE | 20260801 | 10 |
| 111111111 | dr.dupont@cabinet-medical.fr | BNPAFRPP | FR7630001007941234567890185 | DR DUPONT JEAN-PIERRE | 127,50 | 20260815 | 4402 | C | MEDECIN_GENERALISTE | ILE_DE_FRANCE | 20260805 | 5 |
| 222222222 | pharmacie.soleil@orange.fr | CRLYFRPP | FR7617806000050612345678014 | PHARMACIE DU SOLEIL | 1842,30 | 20260815 | 4403 | BSB | PHARMACIEN | PACA | 20260802 | 47 |
| 333333333 | dr.martin.cardio@gmail.com | SOGEFRPP | FR7630003036000005123456789 | DR MARTIN SOPHIE | 544,00 | 20260815 | 4404 | CS | CARDIOLOGUE | AUVERGNE_RHONE_ALPES | 20260803 | 8 |
| 444444444 | cabinet.infirmier.bzh@laposte.net | PSSTFRPP | FR7620041010050014567890152 | CABINET INFIRMIER KERNALEGUEN | 372,60 | 20260815 | 4405 | AMI | INFIRMIER | BRETAGNE | 20260804 | 18 |
| 555555555 | kine.bordeaux@outlook.fr | CMCIFRPP | FR7610278060000002345678015 | ROMAIN LEFEVRE KINESITHERAPEUTE | 186,00 | 20260815 | 4406 | AMK | KINESITHERAPEUTE | NOUVELLE_AQUITAINE | 20260806 | 6 |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+',
'EN_ATTENTE');

-- ============================================================================
-- BORDEREAU 2: Fichier avec anomalie de montant (pour déclencher le ML)
-- Scénario: Un pharmacien facture un montant anormalement élevé
-- ============================================================================
INSERT INTO bordereaux_inbox (nom_fichier, contenu, statut) VALUES (
'SEPA_VIREMENT_AXA_20260815_002.ok',
'| VIREMENTS  COMPTE EMETTEUR : CC654321 FR76120060000012345678901 LE 15/08/2026 |
| MAIL EMETTEUR : paiements@axa-sante.fr |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| N°PS | EMAIL | BIC | IBAN | INTITULE | MONTANT | DATE_VIR | NUMVIR | CODE_ACTE | SPECIALITE | REGION | DATE_SOIN | NB_ACTES |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 666666666 | medecin.lyon@gmail.com | AGRIFRPP | FR7614506000070612345678097 | DR BENALI KARIM | 76,00 | 20260815 | 5501 | C | MEDECIN_GENERALISTE | AUVERGNE_RHONE_ALPES | 20260808 | 3 |
| 777777777 | dentiste.paris@cabinet.fr | BNPAFRPP | FR7630001007941234567890185 | DR MOREAU DENTISTE | 312,00 | 20260815 | 5502 | CS | CHIRURGIEN_DENTISTE | ILE_DE_FRANCE | 20260807 | 4 |
| 222222222 | pharmacie.soleil@orange.fr | CRLYFRPP | FR7617806000050612345678014 | PHARMACIE DU SOLEIL | 9450,00 | 20260815 | 5503 | BSB | PHARMACIEN | PACA | 20260809 | 3 |
| 888888888 | sage.femme.nantes@yahoo.fr | CCBPFRPP | FR7610807000010012345678025 | MARIE LAMBERT SAGE-FEMME | 198,00 | 20260815 | 5504 | V | SAGE_FEMME | PAYS_DE_LA_LOIRE | 20260810 | 6 |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+',
'EN_ATTENTE');

