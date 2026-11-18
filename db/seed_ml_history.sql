-- ============================================================================
-- CETIP - Seed ML Historical Data
-- Populates dim_ps and historical_traitements with realistic data for 12 PS.
-- Used to train the ML models (Isolation Forest / Z-Score).
-- ============================================================================

-- 1. Insert into dim_ps (Ignore duplicates)
INSERT INTO dim_ps (num_ps, email, intitule, specialite, region, bic, iban) VALUES
('111111111', 'dr.dupont@cabinet-medical.fr', 'DR DUPONT JEAN-PIERRE', 'MEDECIN_GENERALISTE', 'ILE_DE_FRANCE', 'BNPAFRPP', 'FR7630001007941234567890185'),
('222222222', 'pharmacie.soleil@orange.fr', 'PHARMACIE DU SOLEIL', 'PHARMACIEN', 'PACA', 'CRLYFRPP', 'FR7617806000050612345678014'),
('333333333', 'dr.martin.cardio@gmail.com', 'DR MARTIN SOPHIE', 'CARDIOLOGUE', 'AUVERGNE_RHONE_ALPES', 'SOGEFRPP', 'FR7630003036000005123456789'),
('444444444', 'cabinet.infirmier.bzh@laposte.net', 'CABINET INFIRMIER KERNALEGUEN', 'INFIRMIER', 'BRETAGNE', 'PSSTFRPP', 'FR7620041010050014567890152'),
('555555555', 'kine.bordeaux@outlook.fr', 'ROMAIN LEFEVRE KINESITHERAPEUTE', 'KINESITHERAPEUTE', 'NOUVELLE_AQUITAINE', 'CMCIFRPP', 'FR7610278060000002345678015'),
('666666666', 'medecin.lyon@gmail.com', 'DR BENALI KARIM', 'MEDECIN_GENERALISTE', 'AUVERGNE_RHONE_ALPES', 'AGRIFRPP', 'FR7614506000070612345678097'),
('777777777', 'dentiste.paris@cabinet.fr', 'DR MOREAU DENTISTE', 'CHIRURGIEN_DENTISTE', 'ILE_DE_FRANCE', 'BNPAFRPP', 'FR7630001007941234567890185'),
('888888888', 'sage.femme.nantes@yahoo.fr', 'MARIE LAMBERT SAGE-FEMME', 'SAGE_FEMME', 'PAYS_DE_LA_LOIRE', 'CCBPFRPP', 'FR7610807000010012345678025'),
('123456789', 'jean.dupont@cabinet-medical.fr', 'CABINET DUPONT', 'MEDECIN_GENERALISTE', 'ILE_DE_FRANCE', 'CECEPAPP', 'FR7630004000123456789012345'),
('987654321', 'marie.curie@clinique.fr', 'CLINIQUE CURIE', 'INFIRMIER', 'PACA', 'BNPAFRPP', 'FR7630004001123456789012345'),
('456789123', 'mauvais.email@', 'LABORATOIRE EXEMPLE', 'PHARMACIEN', 'BRETAGNE', 'SOGENFRP', 'FR7630004002123456789012345'),
('999999999', 'docteur.anomalie@hospital.fr', 'HOPITAL ANOMALIE', 'CHIRURGIEN', 'CORSE', 'CREDITPP', 'FR7630004003123456789012345')
ON CONFLICT (num_ps) DO NOTHING;

-- 2. Clear historical data just in case
TRUNCATE historical_traitements RESTART IDENTITY CASCADE;

-- 3. Insert mock historical data
DO $$ 
DECLARE
    -- Cursor over our PS to generate history
    ps_record RECORD;
    i INTEGER;
    base_price NUMERIC;
    base_actes INTEGER;
    v_montant NUMERIC(10,2);
    v_nb_actes INTEGER;
    v_montant_par_acte NUMERIC(10,2);
    v_code_acte VARCHAR;
BEGIN
    FOR ps_record IN SELECT * FROM dim_ps LOOP
        -- Define base profile per specialty
        IF ps_record.specialite = 'MEDECIN_GENERALISTE' THEN
            base_price := 26.50; base_actes := 4; v_code_acte := 'C';
        ELSIF ps_record.specialite = 'PHARMACIEN' THEN
            base_price := 40.00; base_actes := 30; v_code_acte := 'BSB';
        ELSIF ps_record.specialite = 'CARDIOLOGUE' THEN
            base_price := 51.00; base_actes := 5; v_code_acte := 'CS';
        ELSIF ps_record.specialite = 'INFIRMIER' THEN
            base_price := 9.00; base_actes := 15; v_code_acte := 'AMI';
        ELSIF ps_record.specialite = 'KINESITHERAPEUTE' THEN
            base_price := 16.50; base_actes := 10; v_code_acte := 'AMK';
        ELSIF ps_record.specialite = 'CHIRURGIEN_DENTISTE' THEN
            base_price := 35.00; base_actes := 8; v_code_acte := 'CS';
        ELSIF ps_record.specialite = 'SAGE_FEMME' THEN
            base_price := 33.00; base_actes := 6; v_code_acte := 'V';
        ELSIF ps_record.specialite = 'CHIRURGIEN' THEN
            base_price := 300.00; base_actes := 2; v_code_acte := 'CS';
        ELSE
            base_price := 25.00; base_actes := 5; v_code_acte := 'C';
        END IF;

        -- Generate 25 records per PS
        FOR i IN 1..25 LOOP
            -- Introduce some natural variance (+/- 15%)
            v_nb_actes := base_actes + (random() * (base_actes * 0.3) - (base_actes * 0.15))::INTEGER;
            IF v_nb_actes < 1 THEN v_nb_actes := 1; END IF;
            
            v_montant_par_acte := base_price + (random() * (base_price * 0.1) - (base_price * 0.05));
            v_montant := (v_nb_actes * v_montant_par_acte);
            
            INSERT INTO historical_traitements (
                num_ps, specialite, region, code_acte, montant, nb_actes, montant_par_acte, date_traitement, mois, annee
            ) VALUES (
                ps_record.num_ps, 
                ps_record.specialite, 
                ps_record.region, 
                v_code_acte, 
                ROUND(v_montant, 2), 
                v_nb_actes, 
                ROUND(v_montant_par_acte, 2), 
                CURRENT_DATE - (i || ' days')::interval,
                EXTRACT(MONTH FROM CURRENT_DATE - (i || ' days')::interval),
                EXTRACT(YEAR FROM CURRENT_DATE - (i || ' days')::interval)
            );
        END LOOP;
    END LOOP;
END $$;
