#!/usr/bin/env python3
"""
scripts/generate_test_data.py
CETIP Bordereau Workflow - Data Generation Script

This script generates:
1. Historical training data (10,000 rows) and inserts it into PostgreSQL.
2. 5 test scenarios (bordereaux files) with specific edge cases.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from pathlib import Path

# Fix seed for reproducibility
np.random.seed(42)
random.seed(42)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cetip:cetip2026@localhost:5432/cetip_db")

# PS Profiles Definitions
PROFILES = [
    {
        "num_ps": "111111111",
        "specialite": "MEDECIN_GENERALISTE",
        "region": "ILE_DE_FRANCE",
        "email": "medecin.idf@exemple.fr",
        "iban": "FR1111111111111111111111111",
        "bic": "BIDAXXXXXXX",
        "intitule": "DR DUPONT GENERALISTE",
        "montant_mean": 275,
        "montant_std": 60,
        "code_acte_opts": ["C", "CS"]
    },
    {
        "num_ps": "222222222",
        "specialite": "PHARMACIEN",
        "region": "PACA",
        "email": "pharma.paca@exemple.fr",
        "iban": "FR2222222222222222222222222",
        "bic": "BIDBXXXXXXX",
        "intitule": "PHARMACIE DU SOLEIL",
        "montant_mean": 110,
        "montant_std": 30,
        "code_acte_opts": ["BSB"]
    },
    {
        "num_ps": "333333333",
        "specialite": "KINESITHERAPEUTE",
        "region": "AUVERGNE_RHONE_ALPES",
        "email": "kine.aura@exemple.fr",
        "iban": "FR3333333333333333333333333",
        "bic": "BIDCXXXXXXX",
        "intitule": "CABINET KINE AURA",
        "montant_mean": 100,
        "montant_std": 20,
        "code_acte_opts": ["AMK"]
    },
    {
        "num_ps": "444444444",
        "specialite": "CARDIOLOGUE",
        "region": "ILE_DE_FRANCE",
        "email": "cardio.idf@exemple.fr",
        "iban": "FR4444444444444444444444444",
        "bic": "BIDDXXXXXXX",
        "intitule": "DR MARTIN CARDIOLOGUE",
        "montant_mean": 550,
        "montant_std": 120,
        "code_acte_opts": ["CS"]
    },
    {
        "num_ps": "555555555",
        "specialite": "INFIRMIER",
        "region": "BRETAGNE",
        "email": "infirmier.bzh@exemple.fr",
        "iban": "FR5555555555555555555555555",
        "bic": "BIDEXXXXXXX",
        "intitule": "CABINET INFIRMIER BRETAGNE",
        "montant_mean": 65,
        "montant_std": 15,
        "code_acte_opts": ["AIS", "AMI"]
    }
]

def generate_historical_data():
    print("==================================================")
    print("PART 1: Generating historical training data...")
    records = []
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 30)
    days_range = (end_date - start_date).days

    # Generate 10,000 rows across 5 PS -> 2000 per PS
    for profile in PROFILES:
        for _ in range(2000):
            treatment_date = start_date + timedelta(days=random.randint(0, days_range))
            
            # Use normal distribution, but clip at 0 to avoid negative amounts
            montant = max(10, np.random.normal(profile["montant_mean"], profile["montant_std"]))
            code_acte = random.choice(profile["code_acte_opts"])
            nb_actes = random.randint(1, 5)
            montant_par_acte = montant / nb_actes
            
            records.append({
                "num_ps": profile["num_ps"],
                "specialite": profile["specialite"],
                "region": profile["region"],
                "code_acte": code_acte,
                "montant": round(montant, 2),
                "nb_actes": nb_actes,
                "montant_par_acte": round(montant_par_acte, 2),
                "date_traitement": treatment_date.date(),
                "mois": treatment_date.month,
                "annee": treatment_date.year
            })

    df = pd.DataFrame(records)
    print(f"-> Generated {len(df)} rows.")
    
    print("-> Connecting to PostgreSQL...")
    try:
        engine = create_engine(DATABASE_URL)
        df.to_sql('historical_traitements', engine, if_exists='append', index=False)
        print("-> Historical data inserted successfully!")
    except Exception as e:
        print(f"-> [ERROR] Failed to insert historical data: {e}")
        print("-> Make sure PostgreSQL is running and DATABASE_URL is correct.")
        print(f"-> DATABASE_URL used: {DATABASE_URL}")

def create_bordereau_content(rows_data):
    # As per Enriched Schema Option B
    header_1 = "| VIREMENTS  COMPTE EMETTEUR : CC123456 FR98765432109876543210987 LE 05/08/2026 |"
    header_2 = "| MAIL EMETTEUR : cetip-emetteur@cegedim.com |"
    separator = "+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+"
    col_names = "| N°PS | EMAIL | BIC | IBAN | INTITULE | MONTANT | DATE_VIR | NUMVIR | CODE_ACTE | SPECIALITE | REGION | DATE_SOIN | NB_ACTES |"
    
    lines = [header_1, header_2, separator, col_names, separator]
    
    for row in rows_data:
        numvir = row.get("numvir", str(random.randint(1000, 9999)))
        line = f"| {row['num_ps']} | {row['email']} | {row['bic']} | {row['iban']} | {row['intitule']} | {row['montant']} | {row['date_vir']} | {numvir} | {row['code_acte']} | {row['specialite']} | {row['region']} | {row['date_soin']} | {row['nb_actes']} |"
        lines.append(line)
        
    lines.append(separator)
    return "\n".join(lines)

def generate_test_files():
    print("\n==================================================")
    print("PART 2: Generating test scenario files...")
    
    output_dir = Path("data/test_scenarios")
    output_dir.mkdir(parents=True, exist_ok=True)
    ps_map = {p["num_ps"]: p for p in PROFILES}
    
    def get_base_row(ps_num, montant, date_vir="20260805", date_soin="20260720", nb_actes="1"):
        p = ps_map.get(ps_num, {
            "num_ps": ps_num,
            "email": f"ps{ps_num}@gmail.com",
            "bic": "BUNKNOWNXXX",
            "iban": "FRUNKNOWNXXXXXXXXXXXX",
            "intitule": "UNKNOWN PS",
            "code_acte_opts": ["C"],
            "specialite": "GENERALISTE",
            "region": "UNKNOWN"
        })
        return {
            "num_ps": p["num_ps"],
            "email": p["email"],
            "bic": p["bic"],
            "iban": p["iban"],
            "intitule": p["intitule"],
            "montant": montant,
            "date_vir": date_vir,
            "code_acte": p["code_acte_opts"][0],
            "specialite": p["specialite"],
            "region": p["region"],
            "date_soin": date_soin,
            "nb_actes": nb_actes
        }

    summary = []
    
    # SCENARIO 1: test1_all_valid.txt
    rows_test1 = []
    for p in PROFILES:
        rows_test1.append(get_base_row(p["num_ps"], f"{int(p['montant_mean'])},00"))
        rows_test1.append(get_base_row(p["num_ps"], f"{int(p['montant_mean']+10)},50"))
    
    (output_dir / "test1_all_valid.txt").write_text(create_bordereau_content(rows_test1), encoding="utf-8")
    summary.append("1. test1_all_valid.txt: 10 rows -> All 5 PS are valid and amounts are normal.")
    
    # SCENARIO 2: test2_format_error.txt
    rows_test2 = rows_test1.copy()
    for r in rows_test2:
        if r["num_ps"] == "222222222":
            r["montant"] = "INVALID_AMOUNT"
            break
    (output_dir / "test2_format_error.txt").write_text(create_bordereau_content(rows_test2), encoding="utf-8")
    summary.append("2. test2_format_error.txt: 10 rows -> PS 222222222 has a format error (will be rejected).")
    
    # SCENARIO 3: test3_missing_field.txt
    rows_test3 = rows_test1.copy()
    for r in rows_test3:
        if r["num_ps"] == "333333333":
            r["email"] = " " # Empty field
            break
    (output_dir / "test3_missing_field.txt").write_text(create_bordereau_content(rows_test3), encoding="utf-8")
    summary.append("3. test3_missing_field.txt: 10 rows -> PS 333333333 has an empty email field (will be rejected).")
    
    # SCENARIO 4: test4_anomaly_amounts.txt
    rows_test4 = rows_test1.copy()
    for r in rows_test4:
        if r["num_ps"] == "111111111":
            r["montant"] = "95000,00" # Severe anomaly
        elif r["num_ps"] == "444444444":
            r["montant"] = "500000,00" # Severe anomaly
    (output_dir / "test4_anomaly_amounts.txt").write_text(create_bordereau_content(rows_test4), encoding="utf-8")
    summary.append("4. test4_anomaly_amounts.txt: 10 rows -> PS 111111111 and 444444444 have extreme anomaly amounts (ML will flag them).")

    # SCENARIO 5: test5_mixed.txt
    rows_test5 = [
        get_base_row("111111111", "250,00"),              # Valid
        get_base_row("222222222", "ERROR"),               # Format error -> Rejected
        get_base_row("333333333", "120,00"),              # Valid
        get_base_row("444444444", "80000,00"),            # Anomaly amount -> ML Flags it
        get_base_row("555555555", "70,00")                # Base row for missing field
    ]
    rows_test5[-1]["email"] = " "                         # Manually override the email to test missing field
    
    (output_dir / "test5_mixed.txt").write_text(create_bordereau_content(rows_test5), encoding="utf-8")
    summary.append("5. test5_mixed.txt: 5 rows -> Mixed statuses (2 Valid, 1 Anomaly, 2 Rejected).")

    # SCENARIO 6: test6_new_ps_no_history.txt — Tests HISTORIQUE_INSUFFISANT path
    rows_test6 = [
        get_base_row("111111111", "250,00"),              # Known PS, valid
        get_base_row("666666666", "350,00"),              # NEW PS with ZERO historical data
        get_base_row("666666666", "420,00"),              # Another line for the new PS
    ]
    # Override the new PS's details
    for r in rows_test6:
        if r["num_ps"] == "666666666":
            r["intitule"] = "DR NOUVEAU PRATICIEN"
            r["specialite"] = "DERMATOLOGUE"
            r["region"] = "OCCITANIE"
    (output_dir / "test6_new_ps_no_history.txt").write_text(create_bordereau_content(rows_test6), encoding="utf-8")
    summary.append("6. test6_new_ps_no_history.txt: 3 rows -> PS 666666666 has no history (ML returns HISTORIQUE_INSUFFISANT).")
    
    print("\n--- Summary ---")
    for s in summary:
        print(s)

if __name__ == "__main__":
    try:
        import pandas
        import sqlalchemy
        import psycopg2
    except ImportError:
        print("[ERROR] Missing required libraries. Run: pip install pandas sqlalchemy psycopg2-binary")
        exit(1)
        
    generate_historical_data()
    generate_test_files()
    print("\n[SUCCESS] Script completed successfully!")
