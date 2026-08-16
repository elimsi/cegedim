-- =============================================================================
-- CETIP / Cegedim - Schéma PostgreSQL - Kimball Star Schema
-- =============================================================================

-- 1. Nettoyage sécurisé pour re-runs (Ordre de suppression respectant les FK)
DROP TABLE IF EXISTS fact_traitements CASCADE;
DROP TABLE IF EXISTS historical_traitements CASCADE;
DROP TABLE IF EXISTS dim_ps CASCADE;
DROP TABLE IF EXISTS dim_actes CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS bronze_bordereaux CASCADE;
DROP TABLE IF EXISTS bordereaux_inbox CASCADE;

-- =============================================================================
-- 2. TABLES DIMENSIONNELLES
-- =============================================================================

-- Dimension Date
CREATE TABLE dim_date (
    date_id INTEGER PRIMARY KEY, -- Format YYYYMMDD
    jour INTEGER,
    mois INTEGER,
    trimestre INTEGER,
    annee INTEGER,
    semaine INTEGER
);

-- Fonction pour peupler dim_date
CREATE OR REPLACE FUNCTION populate_dim_date(start_date DATE, end_date DATE)
RETURNS VOID AS $$
DECLARE
    curr_date DATE := start_date;
BEGIN
    WHILE curr_date <= end_date LOOP
        INSERT INTO dim_date (date_id, jour, mois, trimestre, annee, semaine)
        VALUES (
            to_char(curr_date, 'YYYYMMDD')::INTEGER,
            EXTRACT(DAY FROM curr_date),
            EXTRACT(MONTH FROM curr_date),
            EXTRACT(QUARTER FROM curr_date),
            EXTRACT(YEAR FROM curr_date),
            EXTRACT(WEEK FROM curr_date)
        )
        ON CONFLICT (date_id) DO NOTHING;
        
        curr_date := curr_date + INTERVAL '1 day';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Peuplement de dim_date pour 2023-2026
SELECT populate_dim_date('2023-01-01', '2026-12-31');


-- Dimension Actes Médicaux
CREATE TABLE dim_actes (
    code_acte VARCHAR PRIMARY KEY,
    libelle VARCHAR,
    categorie VARCHAR
);

-- Insertion des actes médicaux standards français
INSERT INTO dim_actes (code_acte, libelle, categorie) VALUES
('C', 'Consultation', 'Médecine Générale'),
('CS', 'Consultation Spécialiste', 'Spécialiste'),
('V', 'Visite', 'Médecine Générale'),
('AIS', 'Acte Infirmier Soins', 'Infirmier'),
('AMK', 'Acte Masso-Kinésithérapie', 'Kinésithérapie'),
('AMI', 'Acte Médico-Infirmier', 'Infirmier'),
('BSB', 'Bilan Sanguin Base', 'Biologie')
ON CONFLICT (code_acte) DO NOTHING;


-- Dimension Professionnels de Santé (PS)
CREATE TABLE dim_ps (
    num_ps VARCHAR PRIMARY KEY,
    email VARCHAR,
    intitule VARCHAR,
    specialite VARCHAR,
    region VARCHAR,
    bic VARCHAR,
    iban VARCHAR
);

-- =============================================================================
-- 3. TABLES DE FAITS ET HISTORIQUES
-- =============================================================================

-- Table de Faits : Traitements (Bordereaux)
CREATE TABLE fact_traitements (
    id SERIAL PRIMARY KEY,
    date_execution TIMESTAMP DEFAULT NOW(),
    date_vir_id INTEGER REFERENCES dim_date(date_id),
    date_soin_id INTEGER REFERENCES dim_date(date_id),
    num_ps VARCHAR REFERENCES dim_ps(num_ps),
    code_acte VARCHAR REFERENCES dim_actes(code_acte),
    num_virement VARCHAR,
    montant NUMERIC(10,2),
    nb_actes INTEGER,
    statut VARCHAR CHECK (statut IN ('VALIDE', 'REJETE')),
    raison_rejet VARCHAR NULL,
    flag_anomalie VARCHAR NULL,
    score_anomalie NUMERIC(4,3) NULL,
    montant_moyen_historique_ps NUMERIC(10,2) NULL,
    ecart_vs_historique NUMERIC(6,2) NULL,
    fichier_source VARCHAR,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMP NULL,
    reviewed_by VARCHAR(100) NULL
);

-- Table : Données Historiques (Training Data ML)
CREATE TABLE historical_traitements (
    id SERIAL PRIMARY KEY,
    num_ps VARCHAR,
    specialite VARCHAR,
    region VARCHAR,
    code_acte VARCHAR,
    montant NUMERIC(10,2),
    nb_actes INTEGER,
    montant_par_acte NUMERIC(10,2),
    date_traitement DATE,
    mois INTEGER,
    annee INTEGER
);

-- =============================================================================
-- 4. INDEX DE PERFORMANCE
-- =============================================================================
CREATE INDEX idx_fact_statut ON fact_traitements(statut);
CREATE INDEX idx_fact_flag_anomalie ON fact_traitements(flag_anomalie);
CREATE INDEX idx_fact_date_execution ON fact_traitements(date_execution);
CREATE INDEX idx_fact_num_ps ON fact_traitements(num_ps);

-- =============================================================================
-- 5. TABLES DE RECEPTION (INBOX)
-- =============================================================================
CREATE TABLE IF NOT EXISTS bordereaux_inbox (
    id SERIAL PRIMARY KEY,
    nom_fichier VARCHAR(255) NOT NULL,
    contenu TEXT NOT NULL,
    statut VARCHAR(20) DEFAULT 'EN_ATTENTE'
        CHECK (statut IN ('EN_ATTENTE', 'EN_COURS', 'TRAITE', 'ERREUR')),
    date_reception TIMESTAMP DEFAULT NOW(),
    date_traitement TIMESTAMP NULL
);

-- =============================================================================
-- 6. BRONZE LAYER (raw ingestion — Medallion Architecture)
-- =============================================================================
CREATE TABLE IF NOT EXISTS bronze_bordereaux (
    id SERIAL PRIMARY KEY,
    num_ps VARCHAR(20),
    email VARCHAR(255),
    intitule VARCHAR(255),
    specialite VARCHAR(100),
    region VARCHAR(100),
    bic VARCHAR(20),
    iban VARCHAR(35),
    montant NUMERIC(12, 2),
    nb_actes INTEGER,
    code_acte VARCHAR(10),
    date_vir VARCHAR(20),
    date_soin VARCHAR(20),
    numvir VARCHAR(20),
    flag_anomalie VARCHAR(30),
    score_anomalie NUMERIC(6, 4),
    anomalie_semantique TEXT,
    fichier_source VARCHAR(255),
    date_ingestion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bronze_num_ps ON bronze_bordereaux(num_ps);
CREATE INDEX IF NOT EXISTS idx_bronze_date_ingestion ON bronze_bordereaux(date_ingestion);

