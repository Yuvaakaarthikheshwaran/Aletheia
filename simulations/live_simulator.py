import time
import requests
import json
import os

samples = [
    {
        "time": "08:00",
        "air_temp": 28,
        "humidity": 72,
        "light": 300,
        "leaf_temp": 29,
        "soil_moisture": 72,
        "soil_temp": 24,
        "air_temp_rate": 0,
        "humidity_rate": 0,
        "leaf_temp_rate": 0
    },
    {
        "time": "10:00",
        "air_temp": 31,
        "humidity": 60,
        "light": 500,
        "leaf_temp": 33,
        "soil_moisture": 68,
        "soil_temp": 27,
        "air_temp_rate": 3,
        "humidity_rate": -12,
        "leaf_temp_rate": 4
    },
    {
        "time": "12:00",
        "air_temp": 36,
        "humidity": 45,
        "light": 750,
        "leaf_temp": 41,
        "soil_moisture": 62,
        "soil_temp": 32,
        "air_temp_rate": 5,
        "humidity_rate": -15,
        "leaf_temp_rate": 8
    },
    {
        "time": "14:00",
        "air_temp": 41,
        "humidity": 28,
        "light": 920,
        "leaf_temp": 48,
        "soil_moisture": 54,
        "soil_temp": 38,
        "air_temp_rate": 5,
        "humidity_rate": -17,
        "leaf_temp_rate": 7
    }
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(BASE_DIR, "../data/live_data.json")
output_path = os.path.abspath(output_path)

print("Writing to:", output_path)

for sample in samples:
    print("\n========================")
    print("Processing:", sample["time"])

    sample["leaf_temp_delta"] = sample["leaf_temp"] - sample["air_temp"]

    print("Sending request...")
    response = requests.post(
        "http://127.0.0.1:5000/predict",
        json=sample
    )

    print("Response status:", response.status_code)

    result = response.json()
    result["time"] = sample["time"]

    print("Writing to file:", output_path)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=4)

    print("Write complete for:", sample["time"])

    time.sleep(3)