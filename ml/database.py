import os
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cetip:cetip2026@localhost:5432/cetip_db")

engine = create_engine(DATABASE_URL)

def get_ps_history(num_ps: str, specialite: str) -> pd.DataFrame:
    """
    Fetch historical data for a specific PS to train the anomaly model.
    Returns all 5 features: montant, nb_actes, montant_par_acte,
    frequence_historique_ps, ecart_montant_moyen_ps.
    Falls back to regional/specialty data if the PS doesn't have enough history.
    """
    query_ps = """
        SELECT montant, nb_actes, montant_par_acte, date_traitement
        FROM historical_traitements 
        WHERE num_ps = %(num_ps)s
        ORDER BY date_traitement
    """
    df = pd.read_sql(query_ps, engine, params={"num_ps": num_ps})
    
    # If PS has less than 10 historical points, expand to their specialty
    if len(df) < 10:
        query_spec = """
            SELECT montant, nb_actes, montant_par_acte, date_traitement
            FROM historical_traitements 
            WHERE specialite = %(specialite)s
            ORDER BY date_traitement
        """
        df = pd.read_sql(query_spec, engine, params={"specialite": specialite})

    if not df.empty:
        # Compute derived features
        mean_montant = df['montant'].mean()
        df['ecart_montant_moyen_ps'] = ((df['montant'] - mean_montant) / mean_montant * 100).round(2)
        df['frequence_historique_ps'] = len(df)
        
    return df

def mark_as_reviewed(transaction_id: int, reviewer: str = "analyst"):
    """Mark a flagged transaction as reviewed (false positive)."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE fact_traitements SET reviewed = TRUE, reviewed_at = NOW(), reviewed_by = :reviewer WHERE id = :tid"),
            {"tid": transaction_id, "reviewer": reviewer}
        )
        conn.commit()


def get_transaction_by_id(transaction_id: int) -> dict | None:
    """Fetch a single transaction by ID for the LLM explain endpoint."""
    query = """
        SELECT f.id, f.num_ps, f.montant, f.nb_actes, f.statut,
               f.flag_anomalie, f.score_anomalie, 0 AS ecart_vs_historique,
               0 AS montant_moyen_historique_ps, f.date_virement AS date_execution, f.fichier_source,
               f.intitule, f.specialite, f.region, f.email,
               f.code_acte
        FROM silver_traitements f
        WHERE f.id = %(id)s
    """
    df = pd.read_sql(query, engine, params={"id": transaction_id})
    if df.empty:
        return None
    return df.iloc[0].to_dict()
