#!/usr/bin/env python3
"""
ml_scoring.py - CETIP Bordereau Workflow
Machine Learning layer using Isolation Forest to detect anomalies in transaction amounts.

Input: JSON via stdin or file path.
Output: JSON via stdout with `score_anomalie` and `is_anomalie` added to each row.
"""

import sys
import json
import pandas as pd
from sklearn.ensemble import IsolationForest

def parse_montant(montant_str):
    try:
        # Convert "123,45" or "123.45" to float
        clean_str = str(montant_str).strip().replace(' ', '').replace(',', '.')
        return float(clean_str)
    except (ValueError, TypeError):
        return 0.0

def process_data(input_data):
    # Ensure rows exist
    # Can work on rows_valides or directly on an array of rows
    rows = []
    if isinstance(input_data, dict):
        if "rows_valides" in input_data:
            rows = input_data["rows_valides"]
        elif "rows" in input_data:
            rows = input_data["rows"]
    elif isinstance(input_data, list):
        rows = input_data

    if not rows:
        return input_data

    # Extract montants
    montants = []
    for r in rows:
        m = parse_montant(r.get("montant", 0))
        montants.append(m)
        
    df = pd.DataFrame({"montant": montants})
    
    # Simple check to avoid running IsolationForest on trivial data lengths
    if len(df) < 5:
        # If very few transactions, everything is normal (or use a pre-trained model ideally)
        for r in rows:
            r["score_anomalie"] = 0.5
            r["is_anomalie"] = False
        return input_data

    # Isolation Forest
    # In a real scenario, this should be pre-trained on historical data. 
    # For the PFE, we train on the current batch (or it can represent a batch scoring).
    model = IsolationForest(contamination=0.1, random_state=42)
    
    # Fit and predict
    # Reshape for sklearn
    X = df[["montant"]].values
    model.fit(X)
    
    # Anomaly scores: Lower scores indicate anomalies
    scores = model.decision_function(X)
    preds = model.predict(X) # -1 for outliers, 1 for inliers
    
    # Enrich the original data
    for i, r in enumerate(rows):
        # Normalize score slightly for easier reading (usually between -0.5 and 0.5)
        score = float(scores[i])
        is_anom = bool(preds[i] == -1)
        
        r["score_anomalie"] = score
        r["is_anomalie"] = is_anom

    return input_data

if __name__ == "__main__":
    # Read from stdin if no file provided
    input_text = ""
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
    elif len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            input_text = f.read()
    else:
        print(json.dumps({"error": "No input data provided."}))
        sys.exit(1)

    if not input_text.strip():
        print(json.dumps({"error": "Empty input data provided."}))
        sys.exit(1)

    try:
        data = json.loads(input_text)
        enriched_data = process_data(data)
        print(json.dumps(enriched_data))
    except Exception as e:
        # On error, just return the input (or fail gracefully)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
