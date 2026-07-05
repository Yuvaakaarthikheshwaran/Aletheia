import joblib
import pandas as pd
import numpy as np

temporal_model = joblib.load("../temporal_ai/aletheia_temporal_v51.pkl")


def detect_anomaly(sensor_data):
    input_df = pd.DataFrame([sensor_data])

    probabilities = temporal_model.predict_proba(input_df)[0]
    max_confidence = float(np.max(probabilities)) * 100

    if max_confidence < 55:
        return {
            "is_unknown": True,
            "confidence": round(max_confidence, 2),
            "warning": "Unknown anomaly detected"
        }

    return {
        "is_unknown": False,
        "confidence": round(max_confidence, 2),
        "warning": None
    }
