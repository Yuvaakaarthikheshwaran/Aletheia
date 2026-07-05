import joblib
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "aletheia_model_v3.pkl")

model = joblib.load(MODEL_PATH)

def calculate_severity(data, prediction):
    score = 0

    air_temp = data["air_temp"]
    leaf_delta = data["leaf_temp_delta"]
    humidity = data["humidity"]
    soil_moisture = data["soil_moisture"]

    if prediction == "heat_stress":
        score += min((air_temp - 30) * 5, 35)
        score += min(leaf_delta * 8, 35)
        score += min((50 - humidity) * 1.2, 30)

    elif prediction == "water_stress":
        score += min((40 - soil_moisture) * 2.5, 50)
        score += min(leaf_delta * 7, 30)

    elif prediction == "root_zone_stress":
        score += min((data["soil_temp"] - 28) * 4, 50)

    elif prediction == "nutrient_lockout":
        score += min((data["soil_temp"] - 25) * 3, 40)

    return max(0, min(100, round(score)))

def get_risk_state(prediction, severity):
    if prediction == "healthy":
        return "healthy"

    if severity <= 15:
        return "early_warning"
    elif severity <= 75:
        return "stress"
    else:
        return "critical"


def explain_prediction(data, prediction):
    reasons = []

    if data["leaf_temp_delta"] > 4:
        reasons.append("Leaf temperature delta is elevated")

    if data["air_temp_rate"] > 2:
        reasons.append("Air temperature is rising rapidly")

    if data["humidity_rate"] < -8:
        reasons.append("Humidity is dropping rapidly")

    if data["soil_moisture"] < 35:
        reasons.append("Soil moisture is critically low")

    if data["soil_temp"] > 35:
        reasons.append("Root-zone temperature is high")

    if not reasons:
        reasons.append("Conditions remain within acceptable range")

    return reasons


def get_recommendation(prediction):
    recommendations = {
        "healthy": "Maintain current conditions",
        "heat_stress": "Increase cooling or misting immediately",
        "water_stress": "Irrigate plant and monitor soil moisture",
        "root_zone_stress": "Cool root zone and inspect soil",
        "nutrient_lockout": "Check nutrient availability and soil chemistry"
    }
    return recommendations.get(prediction, "No recommendation available")


def analyze(data):

    feature_order = [
        "air_temp",
        "humidity",
        "light",
        "leaf_temp",
        "leaf_temp_delta",
        "soil_moisture",
        "soil_temp",
        "air_temp_rate",
        "humidity_rate",
        "leaf_temp_rate"
    ]

    input_df = pd.DataFrame([data])[feature_order]

    prediction = model.predict(input_df)[0]
    confidence = round(max(model.predict_proba(input_df)[0]) * 100, 2)
    severity = calculate_severity(data, prediction)
    risk_state = get_risk_state(prediction, severity)
    reasons = explain_prediction(data, prediction)
    recommendation = get_recommendation(prediction)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "severity": severity,
        "reasons": reasons,
	"risk_state": risk_state,
        "recommendation": recommendation
        
    }


if __name__ == "__main__":
    sample = {
        "air_temp": 40,
        "humidity": 30,
        "light": 900,
        "leaf_temp": 46,
        "leaf_temp_delta": 6,
        "soil_moisture": 50,
        "soil_temp": 37,
        "air_temp_rate": 4,
        "humidity_rate": -12,
        "leaf_temp_rate": 7
    }

    result = analyze(sample)

    for key, value in result.items():
        print(f"{key}: {value}")