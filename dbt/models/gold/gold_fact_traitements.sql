-- =============================================================================
-- dbt Model: gold/gold_fact_traitements.sql
-- CETIP Medallion Architecture — Gold Layer
-- Business-ready aggregated KPIs for Streamlit Dashboard and reporting.
-- =============================================================================

{{ config(materialized='table', schema='gold') }}

WITH silver AS (
    SELECT * FROM {{ ref('silver_traitements') }}
),

-- Aggregate per PS per day
ps_daily_stats AS (
    SELECT
        num_ps,
        specialite,
        region,
        DATE_TRUNC('day', date_virement) AS date_jour,
        COUNT(*) AS nb_transactions,
        SUM(montant) AS montant_journalier,
        AVG(montant) AS montant_moyen,
        MAX(montant) AS montant_max,
        MIN(montant) AS montant_min,
        SUM(CASE WHEN flag_anomalie = 'ANOMALIE' THEN 1 ELSE 0 END) AS nb_anomalies,
        SUM(CASE WHEN incoherence_code_acte THEN 1 ELSE 0 END) AS nb_incoherences_llm,
        AVG(score_anomalie) AS score_moyen,
        MAX(score_anomalie) AS score_max
    FROM silver
    GROUP BY num_ps, specialite, region, DATE_TRUNC('day', date_virement)
),

-- Add global PS stats for comparison
ps_global AS (
    SELECT
        num_ps,
        COUNT(*) AS total_transactions,
        AVG(montant) AS montant_moyen_global,
        STDDEV(montant) AS stddev_montant_global,
        SUM(CASE WHEN flag_anomalie = 'ANOMALIE' THEN 1 ELSE 0 END) AS total_anomalies,
        MAX(date_virement) AS derniere_transaction
    FROM silver
    GROUP BY num_ps
)

SELECT
    s.num_ps,
    s.specialite,
    s.region,
    s.date_jour,
    s.nb_transactions,
    s.montant_journalier,
    s.montant_moyen,
    s.montant_max,
    s.montant_min,
    s.nb_anomalies,
    s.nb_incoherences_llm,
    s.score_moyen,
    s.score_max,
    -- Enrichment from global stats
    g.total_transactions,
    g.montant_moyen_global,
    g.stddev_montant_global,
    g.total_anomalies,
    g.derniere_transaction,
    -- Risk score: combination of ML score + LLM incoherence
    CASE
        WHEN s.nb_anomalies > 0 AND s.nb_incoherences_llm > 0 THEN 'CRITIQUE'
        WHEN s.nb_anomalies > 0 THEN 'ELEVE'
        WHEN s.nb_incoherences_llm > 0 THEN 'MODERE'
        ELSE 'NOMINAL'
    END AS niveau_risque,
    -- Deviation from historical mean (z-score-like)
    CASE
        WHEN g.stddev_montant_global > 0
        THEN ROUND(((s.montant_moyen - g.montant_moyen_global) / g.stddev_montant_global)::numeric, 2)
        ELSE 0
    END AS z_score_journalier,
    NOW() AS updated_at
FROM ps_daily_stats s
LEFT JOIN ps_global g ON s.num_ps = g.num_ps
ORDER BY s.date_jour DESC, niveau_risque DESC
