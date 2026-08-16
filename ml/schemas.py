from pydantic import BaseModel
from typing import Optional

class ClaimInput(BaseModel):
    num_ps: str
    email: str
    bic: str
    iban: str
    intitule: str
    montant: float
    date_vir: Optional[str] = None
    numvir: Optional[str] = None
    code_acte: Optional[str] = None
    specialite: str
    region: str
    date_soin: Optional[str] = None
    nb_actes: int

class AnomalyResponse(BaseModel):
    flag_anomalie: str
    score_anomalie: Optional[float] = None
    montant_moyen_historique_ps: Optional[float] = None
    ecart_vs_historique: Optional[float] = None
    nb_historique_points: int
    methode: str
    shap_values: Optional[dict] = None
