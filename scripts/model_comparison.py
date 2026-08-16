import time
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from tabulate import tabulate

# 1. Generate Mock Historical Data for a PS
np.random.seed(42)
n_history = 50
hist_data = {
    'montant': np.random.normal(loc=150, scale=20, size=n_history),
    'nb_actes': np.random.randint(1, 5, size=n_history)
}
df_hist = pd.DataFrame(hist_data)
df_hist['montant_par_acte'] = df_hist['montant'] / df_hist['nb_actes']
df_hist['frequence_historique_ps'] = n_history
mean_hist = df_hist['montant'].mean()
df_hist['ecart_montant_moyen_ps'] = ((df_hist['montant'] - mean_hist) / mean_hist) * 100

FEATURES = ['montant', 'nb_actes', 'montant_par_acte', 'frequence_historique_ps', 'ecart_montant_moyen_ps']
X_train = df_hist[FEATURES]

# 2. Define Test Scenarios
# Test 1: Normal claim (should be NORMAL)
test1 = {
    'montant': 160.0,
    'nb_actes': 2,
    'montant_par_acte': 80.0,
    'frequence_historique_ps': n_history,
    'ecart_montant_moyen_ps': ((160.0 - mean_hist) / mean_hist) * 100
}

# Test 4: Anomaly Amount (should be ANOMALY)
test4 = {
    'montant': 850.0,
    'nb_actes': 1,
    'montant_par_acte': 850.0,
    'frequence_historique_ps': n_history,
    'ecart_montant_moyen_ps': ((850.0 - mean_hist) / mean_hist) * 100
}

X_test = pd.DataFrame([test1, test4])
y_true = [1, -1]  # 1 = normal, -1 = anomaly

# 3. Models
results = []

# A. Z-Score (Custom implementation)
def z_score_predict(X_test, X_train, threshold=3.0):
    mean_val = X_train['montant'].mean()
    std_val = X_train['montant'].std()
    predictions = []
    for val in X_test['montant']:
        z = (val - mean_val) / std_val
        predictions.append(-1 if abs(z) > threshold else 1)
    return predictions

start = time.perf_counter()
y_pred_z = z_score_predict(X_test, X_train)
time_z = time.perf_counter() - start
anomalies_detected_z = sum(1 for p, t in zip(y_pred_z, y_true) if p == -1 and t == -1)
false_positives_z = sum(1 for p, t in zip(y_pred_z, y_true) if p == -1 and t == 1)

results.append(["Z-Score", f"{anomalies_detected_z}/1", false_positives_z, f"{time_z:.4f}s", "✅ Haute", "❌ Faible"])

# B. Local Outlier Factor (LOF)
start = time.perf_counter()
# LOF doesn't have a direct predict method for new data easily without novelty=True. 
# We fit with novelty=True to evaluate new samples.
lof = LocalOutlierFactor(n_neighbors=20, contamination=0.05, novelty=True)
lof.fit(X_train)
y_pred_lof = lof.predict(X_test)
time_lof = time.perf_counter() - start
anomalies_detected_lof = sum(1 for p, t in zip(y_pred_lof, y_true) if p == -1 and t == -1)
false_positives_lof = sum(1 for p, t in zip(y_pred_lof, y_true) if p == -1 and t == 1)

results.append(["Local Outlier Factor", f"{anomalies_detected_lof}/1", false_positives_lof, f"{time_lof:.4f}s", "⚠️ Moyenne", "✅ Haute"])

# C. Isolation Forest
start = time.perf_counter()
iso = IsolationForest(contamination=0.05, random_state=42)
iso.fit(X_train)
y_pred_iso = iso.predict(X_test)
time_iso = time.perf_counter() - start
anomalies_detected_iso = sum(1 for p, t in zip(y_pred_iso, y_true) if p == -1 and t == -1)
false_positives_iso = sum(1 for p, t in zip(y_pred_iso, y_true) if p == -1 and t == 1)

results.append(["Isolation Forest", f"{anomalies_detected_iso}/1", false_positives_iso, f"{time_iso:.4f}s", "⚠️ Moyenne", "✅ Haute"])


# 4. Print Results
headers = ["Modèle", "Anomalies détectées", "Faux positifs", "Temps d'exécution", "Interprétabilité", "Robustesse (Non-Normal)"]
print("\n--- RÉSULTATS DE LA COMPARAISON DES MODÈLES ML ---\n")
print(tabulate(results, headers=headers, tablefmt="github"))
print("\n")
