-- =============================================================================
-- dbt Model: silver/silver_traitements.sql
-- CETIP Medallion Architecture — Silver Layer
-- Cleans, deduplicates, and enriches raw bronze data.
-- Applied business rules: type casting, flag normalization, semantic anomaly capture.
-- =============================================================================

{{ config(materialized='table', schema='silver') }}

WITH bronze AS (
    SELECT
        id,
        num_ps,
        TRIM(email) AS email,
        TRIM(intitule) AS intitule,
        UPPER(TRIM(specialite)) AS specialite,
        UPPER(TRIM(region)) AS region,
        TRIM(bic) AS bic,
        TRIM(iban) AS iban,
        montant,
        nb_actes,
        UPPER(TRIM(code_acte)) AS code_acte,
        -- Parse date strings (YYYYMMDD) to proper DATE type
        TO_DATE(NULLIF(date_vir, ''), 'YYYYMMDD') AS date_virement,
        TO_DATE(NULLIF(date_soin, ''), 'YYYYMMDD') AS date_soin,
        numvir,
        flag_anomalie,
        score_anomalie,
        anomalie_semantique,
        fichier_source,
        date_ingestion
    FROM {{ source('public', 'bronze_bordereaux') }}
    WHERE num_ps IS NOT NULL AND num_ps != ''
),

deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY num_ps, numvir, date_virement
            ORDER BY date_ingestion DESC
        ) AS rn
    FROM bronze
),

enriched AS (
    SELECT
        id,
        num_ps,
        email,
        intitule,
        specialite,
        region,
        bic,
        iban,
        montant,
        nb_actes,
        -- Safe division
        CASE WHEN nb_actes > 0 THEN ROUND(montant / nb_actes, 2) ELSE montant END AS montant_par_acte,
        code_acte,
        date_virement,
        date_soin,
        numvir,
        fichier_source,
        date_ingestion,
        -- Normalize anomaly flags
        CASE
            WHEN flag_anomalie = 'ANOMALIE' THEN 'ANOMALIE'
            WHEN flag_anomalie = 'HISTORIQUE_INSUFFISANT' THEN 'HISTORIQUE_INSUFFISANT'
            ELSE 'NORMAL'
        END AS flag_anomalie,
        COALESCE(score_anomalie, 0) AS score_anomalie,
        anomalie_semantique,
        -- Business rule: check code_acte / specialite coherence
        CASE
            WHEN specialite IN ('MEDECIN_GENERALISTE', 'CARDIOLOGUE') AND code_acte NOT IN ('C', 'CS', 'V') THEN TRUE
            WHEN specialite = 'INFIRMIER' AND code_acte NOT IN ('AIS', 'AMI') THEN TRUE
            WHEN specialite = 'KINESITHERAPEUTE' AND code_acte NOT IN ('AMK') THEN TRUE
            WHEN specialite = 'PHARMACIEN' AND code_acte NOT IN ('BSB') THEN TRUE
            ELSE FALSE
        END AS incoherence_code_acte,
        'VALIDE' AS statut
    FROM deduped
    WHERE rn = 1
)

SELECT * FROM enriched
