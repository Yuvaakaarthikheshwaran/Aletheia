from flask import Flask, jsonify
from flask_cors import CORS
import random
import sys 
import os 
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
AI_DIR = os.path.abspath(os.path.join(BASE_DIR, "../ai")) 
sys.path.append(AI_DIR)

from unified_engine import unified_analysis
from backend.biology_engine import evaluate_biology
from backend.fuzzy_search import search_plants
from backend.plant_pipeline import get_dynamic_plant_profile


app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return "Aletheia Final Engine Running"


@app.route("/search/<query>")
def search(query):
    return jsonify(search_plants(query))


def generate_data():
    current_data = {
        "air_temp": random.randint(28, 42),
        "humidity": random.randint(25, 75),
        "light": random.randint(300, 1000),
        "leaf_temp": random.randint(30, 45),
        "soil_moisture": random.randint(25, 80),
        "soil_temp": random.randint(22, 35),
        "air_temp_rate": random.randint(0, 6),
        "humidity_rate": random.randint(-20, 5),
        "leaf_temp_rate": random.randint(0, 5),
        "leaf_temp_delta": random.randint(1, 8)
    }

    temporal_data = {
        "air_temp_prev2": random.randint(28, 35),
        "air_temp_prev1": random.randint(30, 38),
        "air_temp": random.randint(30, 42),

        "humidity_prev2": random.randint(40, 70),
        "humidity_prev1": random.randint(35, 60),
        "humidity": random.randint(25, 55),

        "soil_moisture_prev2": random.randint(40, 80),
        "soil_moisture_prev1": random.randint(35, 70),
        "soil_moisture": random.randint(20, 65),

        "leaf_temp_delta_prev2": random.randint(1, 4),
        "leaf_temp_delta_prev1": random.randint(2, 6),
        "leaf_temp_delta": random.randint(3, 9)
    }

    return current_data, temporal_data


@app.route("/predict/<plant_name>/<growth_stage>/<phase>")
def predict(plant_name, growth_stage, phase):
    current_data, temporal_data = generate_data()

    ai_result = unified_analysis(current_data, temporal_data)

    plant_profile = get_dynamic_plant_profile(plant_name)

    print("\n========== PLANT PROFILE ==========")
    print(plant_profile)
    print("===================================\n")	

    biology_result = evaluate_biology(
        current_data,
        plant_profile,
        growth_stage,
	phase
    )

    return jsonify({
        "sensor_data": current_data,
        "ai_result": ai_result,
        "biology_result": biology_result,
        "plant_profile": plant_profile
    })


if __name__ == "__main__":
    app.run(debug=True)