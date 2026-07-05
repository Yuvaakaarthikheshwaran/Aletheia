from anomaly_detector import detect_anomaly

sample = {
    "air_temp_prev2": 46,
    "air_temp_prev1": 12,
    "air_temp": 51,

    "humidity_prev2": 10,
    "humidity_prev1": 92,
    "humidity": 4,

    "soil_moisture_prev2": 99,
    "soil_moisture_prev1": 3,
    "soil_moisture": 87,

    "leaf_temp_delta_prev2": 12,
    "leaf_temp_delta_prev1": -4,
    "leaf_temp_delta": 15
}

result = detect_anomaly(sample)

print(result)
