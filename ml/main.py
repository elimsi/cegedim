import logging
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from schemas import ClaimInput, AnomalyResponse
from database import get_ps_history, mark_as_reviewed, get_transaction_by_id
from model import AnomalyDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "your_api_key_here")
MISTRAL_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app = FastAPI(title="CETIP Fraud Detection API")

# Enable CORS for Streamlit Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = AnomalyDetector()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict-anomaly", response_model=AnomalyResponse)
def predict_anomaly(claim: ClaimInput):
    logger.info(f"Predicting anomaly for PS {claim.num_ps} with amount {claim.montant}")
    
    # Fetch historical data (by PS or Specialty)
    history = get_ps_history(claim.num_ps, claim.specialite)
    
    # Run the Anomaly Detector
    result = detector.predict(claim.model_dump(), history)
    
    logger.info(f"Result for {claim.num_ps}: {result['flag_anomalie']} (Score: {result['score_anomalie']}, Method: {result['methode']})")
    
    return result

@app.get("/ps-history/{num_ps}")
def ps_history(num_ps: str):
    """Endpoint used by the Streamlit Dashboard to show historical stats"""
    # Fetch just by num_ps without specialty fallback for raw stats
    history = get_ps_history(num_ps, "")
    
    if history.empty:
        return {"num_ps": num_ps, "count": 0, "mean_montant": 0}
    
    return {
        "num_ps": num_ps,
        "count": len(history),
        "mean_montant": round(history["montant"].mean(), 2),
        "std_montant": round(history["montant"].std(), 2)
    }

class ReviewRequest(BaseModel):
    reviewer: str = "analyst"

@app.post("/review/{transaction_id}")
def review_transaction(transaction_id: int, req: ReviewRequest):
    """Mark a flagged transaction as reviewed (false positive)."""
    logger.info(f"Marking transaction {transaction_id} as reviewed by {req.reviewer}")
    mark_as_reviewed(transaction_id, req.reviewer)
    return {"status": "ok", "transaction_id": transaction_id, "reviewed_by": req.reviewer}


@app.post("/llm-explain/{transaction_id}")
async def llm_explain_transaction(transaction_id: int):
    """
    Phase 3 - LLM Agent: Generates a natural language fraud investigation report
    using Mistral AI for a flagged transaction.
    """
    if not MISTRAL_API_KEY:
        raise HTTPException(status_code=503, detail="MISTRAL_API_KEY non configuré")

    # Fetch transaction from DB
    tx = get_transaction_by_id(transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction non trouvée")

    # Fetch PS history
    history = get_ps_history(tx['num_ps'], tx.get('specialite', ''))
    hist_stats = {}
    if not history.empty:
        hist_stats = {
            "nb_transactions": len(history),
            "montant_moyen": round(history['montant'].mean(), 2),
            "montant_std": round(history['montant'].std(), 2),
            "montant_max_historique": round(history['montant'].max(), 2),
        }

    prompt = f"""
Tu es un analyste fraude expert chez CETIP (Cegedim). Redige un rapport d'investigation en français,
professionnel et concis (max 200 mots), pour la transaction suspecte suivante.

Transaction analysée:
- Professionnel de Santé (PS): {tx.get('num_ps')} - {tx.get('intitule', 'N/A')}
- Spécialité: {tx.get('specialite', 'N/A')}, Région: {tx.get('region', 'N/A')}
- Montant de la transaction: {tx.get('montant', 0):.2f} EUR
- Code Acte: {tx.get('code_acte', 'N/A')}
- Score d'anomalie ML: {tx.get('score_anomalie', 0):.4f} (0=normal, 1=anomalie maximale)
- Écart vs historique: {tx.get('ecart_vs_historique', 'N/A')}%
- Détecté le: {tx.get('date_execution', 'N/A')}

Historique du PS ({hist_stats.get('nb_transactions', 0)} transactions):
- Montant moyen historique: {hist_stats.get('montant_moyen', 0):.2f} EUR
- Ecart-type: {hist_stats.get('montant_std', 0):.2f} EUR
- Montant max historique: {hist_stats.get('montant_max_historique', 0):.2f} EUR

Redège un rapport avec:
1. Synthèse de l'anomalie détectée
2. Facteurs de risque identifies
3. Recommandation claire (Bloquer / Surveiller / Faux positif probable)
"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            MISTRAL_API_URL,
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 400
            }
        )
        resp.raise_for_status()
        data = resp.json()
        report = data["choices"][0]["message"]["content"]

    logger.info(f"LLM report generated for transaction {transaction_id}")
    return {"transaction_id": transaction_id, "rapport_llm": report, "model_used": "llama-3.1-8b-instant"}

@app.get("/explain-shap/{transaction_id}")
def explain_shap_transaction(transaction_id: int):
    """
    Calculate SHAP values for a specific transaction to explain the anomaly score.
    """
    tx = get_transaction_by_id(transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction non trouvée")
        
    history = get_ps_history(tx['num_ps'], tx.get('specialite', ''))
    
    # We need to construct the claim dict for the predictor
    claim = {
        'montant': tx['montant'],
        'nb_actes': tx['nb_actes']
    }
    
    # Predict and get SHAP values
    result = detector.predict(claim, history)
    
    return {
        "transaction_id": transaction_id,
        "shap_values": result.get("shap_values", None)
    }
