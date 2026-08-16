#!/usr/bin/env python3
"""
CETIP / Cegedim - Utilitaire de conversion des fichiers de virement .OK en .txt
Permet de manipuler, visualiser et injecter facilement les fichiers réels .OK dans n8n.
"""

import os
import sys
import shutil
import glob

def convert_ok_to_txt(source_dir=".", target_dir="data"):
    # Créer le répertoire de destination s'il n'existe pas
    os.makedirs(target_dir, exist_ok=True)
    
    # Trouver tous les fichiers .OK dans le répertoire courant ou dans le répertoire parent
    search_paths = [
        os.path.join(source_dir, "*.OK"),
        os.path.join("..", "*.OK"),
        os.path.join("..", "..", "*.OK"),
        os.path.join("data", "*.OK")
    ]
    
    found_files = []
    for pattern in search_paths:
        found_files.extend(glob.glob(pattern))
        
    found_files = list(set(found_files))
    
    if not found_files:
        print("--> [Convertisseur] Aucun fichier .OK trouvé dans les répertoires scannés.")
        return
        
    for ok_path in found_files:
        base_name = os.path.basename(ok_path)
        txt_name = os.path.splitext(base_name)[0] + ".txt"
        target_path = os.path.join(target_dir, txt_name)
        
        # Copier et convertir en encodage UTF-8 propre
        try:
            with open(ok_path, "r", encoding="utf-8", errors="ignore") as f_in:
                content = f_in.read()
            
            with open(target_path, "w", encoding="utf-8") as f_out:
                f_out.write(content)
                
            print(f"--> [Convertisseur] Fichier converti avec succès :")
            print(f"    Source  : {ok_path}")
            print(f"    Cible   : {target_path}")
            
            # Créer également un alias standard data/sample_bordereau.txt pour n8n
            sample_path = os.path.join(target_dir, "sample_bordereau.txt")
            with open(sample_path, "w", encoding="utf-8") as f_sample:
                f_sample.write(content)
            print(f"    Alias   : {sample_path} (prêt pour n8n)")
            
        except Exception as e:
            print(f"--> [Erreur] Échec lors de la conversion de {ok_path}: {e}")

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "."
    tgt = sys.argv[2] if len(sys.argv) > 2 else "data"
    convert_ok_to_txt(src, tgt)
