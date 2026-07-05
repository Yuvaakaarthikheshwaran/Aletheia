from sensor_guard import validate_sensor_data

sample = {
    "air_temp": 49,
    "humidity": 10,
    "soil_moisture": 55,
    "soil_temp": 28,
    "leaf_temp": 47,
    "light": 900
}

result = validate_sensor_data(sample)

print(result)
