-- =============================================================================
-- CETIP / Cegedim - Pilotage Analytique & Dashboarding (Power BI / Streamlit)
-- 8 Requêtes Analytiques pour l'Observatoire de Performance
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Taux de rejet global par période (Mois)
-- Permet de suivre l'évolution de la conformité des bordereaux.
-- -----------------------------------------------------------------------------
SELECT 
    d.annee,
    d.mois,
    COUNT(f.id) AS total_lignes,
    SUM(CASE WHEN f.statut = 'REJETE' THEN 1 ELSE 0 END) AS lignes_rejetees,
    ROUND((SUM(CASE WHEN f.statut = 'REJETE' THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(f.id), 0), 2) AS taux_rejet_pourcentage
FROM 
    fact_traitements f
JOIN 
    dim_date d ON f.date_execution::DATE = to_date(d.date_id::TEXT, 'YYYYMMDD')
GROUP BY 
    d.annee, d.mois
ORDER BY 
    d.annee DESC, d.mois DESC;

-- -----------------------------------------------------------------------------
-- 2. Top 10 Professionnels de Santé (PS) par nombre de rejets
-- Objectif : cibler l'accompagnement des PS les plus problématiques.
-- -----------------------------------------------------------------------------
SELECT 
    p.num_ps,
    p.intitule,
    p.specialite,
    COUNT(f.id) AS nombre_rejets,
    SUM(f.montant) AS montant_bloque
FROM 
    fact_traitements f
JOIN 
    dim_ps p ON f.num_ps = p.num_ps
WHERE 
    f.statut = 'REJETE'
GROUP BY 
    p.num_ps, p.intitule, p.specialite
ORDER BY 
    nombre_rejets DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- 3. Répartition des causes de rejet
-- Pour comprendre les motifs principaux d'anomalies (format, champ manquant, contagion).
-- -----------------------------------------------------------------------------
SELECT 
    raison_rejet,
    COUNT(id) AS occurrences,
    ROUND((COUNT(id) * 100.0) / SUM(COUNT(id)) OVER(), 2) AS pourcentage_total
FROM 
    fact_traitements
WHERE 
    statut = 'REJETE'
GROUP BY 
    raison_rejet
ORDER BY 
    occurrences DESC;

-- -----------------------------------------------------------------------------
-- 4. Montant total validé par spécialité médicale
-- Permet de voir où va l'essentiel des paiements (Volume financier par métier).
-- -----------------------------------------------------------------------------
SELECT 
    p.specialite,
    COUNT(f.id) AS volume_transactions,
    SUM(f.montant) AS montant_total_valide,
    ROUND(AVG(f.montant), 2) AS montant_moyen_transaction
FROM 
    fact_traitements f
JOIN 
    dim_ps p ON f.num_ps = p.num_ps
WHERE 
    f.statut = 'VALIDE'
GROUP BY 
    p.specialite
ORDER BY 
    montant_total_valide DESC;

-- -----------------------------------------------------------------------------
-- 5. Virements flaggés "ANOMALIE" avec écart vs historique
-- Résultat de la couche Machine Learning (IsolationForest / Z-Score).
-- -----------------------------------------------------------------------------
SELECT 
    f.num_virement,
    p.intitule,
    p.specialite,
    f.montant AS montant_transaction,
    f.montant_moyen_historique_ps,
    f.ecart_vs_historique AS ecart_pourcentage,
    f.score_anomalie,
    f.flag_anomalie
FROM 
    fact_traitements f
JOIN 
    dim_ps p ON f.num_ps = p.num_ps
WHERE 
    f.flag_anomalie = 'ANOMALIE'
ORDER BY 
    f.ecart_vs_historique DESC;

-- -----------------------------------------------------------------------------
-- 6. Distribution des scores d'anomalie (Isolation Forest)
-- Permet d'analyser la répartition des scores pour calibrer le seuil d'alerte.
-- -----------------------------------------------------------------------------
SELECT 
    ROUND(score_anomalie, 1) AS score_bucket,
    COUNT(id) AS nombre_transactions
FROM 
    fact_traitements
WHERE 
    score_anomalie IS NOT NULL
GROUP BY 
    ROUND(score_anomalie, 1)
ORDER BY 
    score_bucket ASC;

-- -----------------------------------------------------------------------------
-- 7. Volume traité par semaine (Time series - Charge de traitement)
-- Utile pour la page 4 de Streamlit et Power BI (Évolution temporelle).
-- -----------------------------------------------------------------------------
SELECT 
    d.annee,
    d.semaine,
    COUNT(f.id) AS volume_hebdomadaire,
    SUM(f.montant) AS montant_hebdomadaire
FROM 
    fact_traitements f
JOIN 
    dim_date d ON f.date_execution::DATE = to_date(d.date_id::TEXT, 'YYYYMMDD')
GROUP BY 
    d.annee, d.semaine
ORDER BY 
    d.annee DESC, d.semaine DESC;

-- -----------------------------------------------------------------------------
-- 8. Clean claim rate par région
-- Pourcentage de transactions passées avec succès dès le premier traitement (sans rejet).
-- -----------------------------------------------------------------------------
SELECT 
    p.region,
    COUNT(f.id) AS volume_total,
    SUM(CASE WHEN f.statut = 'VALIDE' THEN 1 ELSE 0 END) AS volume_clean,
    ROUND((SUM(CASE WHEN f.statut = 'VALIDE' THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(f.id), 0), 2) AS clean_claim_rate
FROM 
    fact_traitements f
JOIN 
    dim_ps p ON f.num_ps = p.num_ps
GROUP BY 
    p.region
ORDER BY 
    clean_claim_rate ASC;
