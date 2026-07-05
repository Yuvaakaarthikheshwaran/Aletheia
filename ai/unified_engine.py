import joblib
import pandas as pd
import numpy as np

from decision_engine import analyze
from sensor_guard import validate_sensor_data

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


def predict_future(sensor_data):
    temporal_input = pd.DataFrame([sensor_data])

    prediction = temporal_model.predict(temporal_input)[0]
    probabilities = temporal_model.predict_proba(temporal_input)[0]

    confidence = max(probabilities) * 100

    return {
        "future_prediction": prediction,
        "future_confidence": round(float(confidence), 2)
    }


def unified_analysis(current_data, temporal_data):
    sensor_result = validate_sensor_data(current_data)
    current_data = sensor_result["repaired_data"]

    if not sensor_result["sensor_ok"]:
        return {
            "status": "sensor_failure",
            "sensor_status": sensor_result
        }

    anomaly_result = detect_anomaly(temporal_data)

    if anomaly_result["is_unknown"]:
        return {
            "status": "unknown_anomaly",
            "sensor_status": sensor_result,
            "anomaly_status": anomaly_result
        }

    current_result = analyze(current_data)
    future_result = predict_future(temporal_data)

    return {
        "status": "ok",
        "sensor_status": sensor_result,
        "current_state": current_result,
        "future_state": future_result
    }