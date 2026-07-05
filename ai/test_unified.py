from unified_engine import unified_analysis

print("NORMAL TEST")
print("=" * 50)

current_data = {
    "air_temp": 31,
    "humidity": 62,
    "light": 500,
    "leaf_temp": 33,
    "soil_moisture": 68,
    "soil_temp": 27,
    "air_temp_rate": 3,
    "humidity_rate": -12,
    "leaf_temp_rate": 4,
    "leaf_temp_delta": 2
}

temporal_data = {
    "air_temp_prev2": 30,
    "air_temp_prev1": 34,
    "air_temp": 38,

    "humidity_prev2": 58,
    "humidity_prev1": 45,
    "humidity": 30,

    "soil_moisture_prev2": 65,
    "soil_moisture_prev1": 58,
    "soil_moisture": 50,

    "leaf_temp_delta_prev2": 2,
    "leaf_temp_delta_prev1": 4,
    "leaf_temp_delta": 7
}

print(unified_analysis(current_data, temporal_data))


print("\nANOMALY TEST")
print("=" * 50)

anomaly_temporal = {
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

print(unified_analysis(current_data, anomaly_temporal))


print("\nMISSING SENSOR TEST")
print("=" * 50)

missing_data = {
    "air_temp": 31,
    "humidity": 62,
    "leaf_temp": 33,
    "soil_moisture": 68,
    "air_temp_rate": 3,
    "humidity_rate": -12,
    "leaf_temp_rate": 4,
    "leaf_temp_delta": 2
}

print(unified_analysis(missing_data, temporal_data))