import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import shap

# The 5 features from CLAUDE.md
FEATURES = ['montant', 'nb_actes', 'montant_par_acte', 'frequence_historique_ps', 'ecart_montant_moyen_ps']

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(
            contamination=0.05, 
            n_estimators=100, 
            random_state=42
        )
        
    def train(self, df: pd.DataFrame):
        """Fits the IsolationForest on the historical dataframe using all 5 features."""
        available = [f for f in FEATURES if f in df.columns]
        features = df[available].copy()
        features = features.fillna(0)
        self.model.fit(features)
        
    def zscore_check(self, montant: float, historique: pd.DataFrame) -> float:
        """Returns z-score of the current montant vs historical montants."""
        mean = historique['montant'].mean()
        std = historique['montant'].std()
        if pd.isna(std) or std == 0:
            return 0.0
        return (montant - mean) / std

    def predict(self, claim: dict, historique: pd.DataFrame) -> dict:
        montant = claim['montant']
        nb_actes = claim['nb_actes']
        
        # 1. Check if history is sufficient
        if len(historique) < 10:
            return {
                "flag_anomalie": "HISTORIQUE_INSUFFISANT",
                "score_anomalie": None,
                "montant_moyen_historique_ps": None,
                "ecart_vs_historique": None,
                "nb_historique_points": len(historique),
                "methode": "HISTORIQUE_INSUFFISANT",
                "shap_values": None
            }
            
        mean = historique['montant'].mean()
        ecart = ((montant - mean) / mean) * 100 if mean > 0 else 0
        
        # 2. Fast Path: Z-Score for extreme anomalies
        z = self.zscore_check(montant, historique)
        if abs(z) > 3:
            return {
                "flag_anomalie": "ANOMALIE",
                "score_anomalie": 1.0,  # Max score for extreme outliers
                "montant_moyen_historique_ps": round(mean, 2),
                "ecart_vs_historique": round(ecart, 2),
                "nb_historique_points": len(historique),
                "methode": "ZSCORE",
                "shap_values": None
            }
            
        # 3. Isolation Forest on all 5 features for nuanced pattern detection
        import joblib
        import os
        model_path = "isolation_forest.joblib"
        
        # Load model if exists (simulating production serialization)
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.train(historique)
            joblib.dump(self.model, model_path)
        
        montant_par_acte = montant / nb_actes if nb_actes > 0 else montant
        frequence = len(historique)
        ecart_montant_moyen = ecart  # Already computed above
        
        test_df = pd.DataFrame([{
            'montant': montant, 
            'nb_actes': nb_actes, 
            'montant_par_acte': montant_par_acte,
            'frequence_historique_ps': frequence,
            'ecart_montant_moyen_ps': ecart_montant_moyen
        }])
        
        # Only use features that were available during training
        available = [f for f in FEATURES if f in historique.columns]
        test_df = test_df[available]
        
        prediction = self.model.predict(test_df)[0]  # 1 (normal) or -1 (anomaly)
        
        # Normalize decision_function for dashboard (0.0 to 1.0 where 1.0 is highly anomalous)
        # decision < 0 is anomaly. 
        decision = self.model.decision_function(test_df)[0]
        normalized_score = max(0.0, min(1.0, 0.5 - decision)) 
        
        flag = "ANOMALIE" if prediction == -1 else "NORMAL"
        
        # Calculate SHAP values for explainability if flagged
        shap_contributions = None
        if flag == "ANOMALIE":
            try:
                explainer = shap.TreeExplainer(self.model)
                shap_values = explainer.shap_values(test_df)
                shap_contributions = {}
                for i, feature in enumerate(available):
                    shap_contributions[feature] = round(float(shap_values[0][i]), 4)
            except Exception as e:
                print(f"Error calculating SHAP values: {e}")
        
        return {
            "flag_anomalie": flag,
            "score_anomalie": round(normalized_score, 3),
            "montant_moyen_historique_ps": round(mean, 2),
            "ecart_vs_historique": round(ecart, 2),
            "nb_historique_points": len(historique),
            "methode": "ISOLATION_FOREST",
            "shap_values": shap_contributions
        }
