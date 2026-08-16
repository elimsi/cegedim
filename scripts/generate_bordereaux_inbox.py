#!/usr/bin/env python3
import sys
import os
import random
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine

# Need to import from generate_test_data
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from generate_test_data import PROFILES, create_bordereau_content, DATABASE_URL

def generate_db_inbox_files(num_files=10):
    print(f"Connecting to database to insert {num_files} files into 'bordereaux_inbox'...")
    engine = create_engine(DATABASE_URL)
    
    ps_map = {p["num_ps"]: p for p in PROFILES}
    
    def get_base_row(ps_num, montant, date_vir="20260805", date_soin="20260720", nb_actes="1"):
        p = ps_map.get(ps_num, PROFILES[0])
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

    records = []
    base_date = datetime(2026, 8, 1)
    
    for i in range(1, num_files + 1):
        # Generate 3 to 8 rows per file
        num_rows = random.randint(3, 8)
        rows_data = []
        
        # Pick a random date
        file_date = base_date + timedelta(days=random.randint(0, 9))
        date_vir = file_date.strftime("%Y%m%d")
        
        for _ in range(num_rows):
            p = random.choice(PROFILES)
            
            # 5% chance of format error
            if random.random() < 0.05:
                montant = "ERROR"
            # 5% chance of severe anomaly
            elif random.random() < 0.05:
                montant = f"{int(p['montant_mean'] * 50)},00"
            else:
                # normal
                montant = f"{int(p['montant_mean'] + random.randint(-20, 20))},00"
                
            rows_data.append(get_base_row(p["num_ps"], montant, date_vir=date_vir))
            
        file_content = create_bordereau_content(rows_data)
        nom_fichier = f"bordereau_import_{date_vir}_{i:03d}.ok"
        
        records.append({
            "nom_fichier": nom_fichier,
            "contenu": file_content,
            "statut": "EN_ATTENTE",
            "date_reception": file_date
        })
        
    df = pd.DataFrame(records)
    df.to_sql("bordereaux_inbox", engine, if_exists="append", index=False)
    print(f"✅ Successfully generated and inserted {num_files} files into bordereaux_inbox.")

if __name__ == "__main__":
    generate_db_inbox_files(10)
