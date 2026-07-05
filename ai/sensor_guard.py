import math

DEFAULT_VALUES = {
    "air_temp": 30,
    "humidity": 50,
    "soil_moisture": 50,
    "soil_temp": 25,
    "leaf_temp": 32,
    "light": 500
}


def validate_sensor_data(data):
    warnings = []
    confidence_penalty = 0
    repaired_data = data.copy()

    required_fields = [
        "air_temp",
        "humidity",
        "soil_moisture",
        "soil_temp",
        "leaf_temp",
        "light"
    ]

    for field in required_fields:
        if field not in repaired_data:
            repaired_data[field] = DEFAULT_VALUES[field]
            warnings.append(f"Missing sensor replaced: {field}")
            confidence_penalty += 15

    for key, value in list(repaired_data.items()):
        if value is None:
            repaired_data[key] = DEFAULT_VALUES.get(key, 0)
            warnings.append(f"Null replaced: {key}")
            confidence_penalty += 15

        elif isinstance(value, float) and math.isnan(value):
            repaired_data[key] = DEFAULT_VALUES.get(key, 0)
            warnings.append(f"NaN replaced: {key}")
            confidence_penalty += 15

    ranges = {
        "air_temp": (0, 60),
        "humidity": (0, 100),
        "soil_moisture": (0, 100),
        "soil_temp": (0, 50),
        "leaf_temp": (0, 60),
        "light": (0, 120000)
    }

    for sensor, (low, high) in ranges.items():
        if sensor in repaired_data:
            value = repaired_data[sensor]
            if value < low or value > high:
                warnings.append(f"Impossible value in {sensor}: {value}")
                confidence_penalty += 25

    sensor_ok = confidence_penalty < 50
    confidence_score = max(0, 100 - confidence_penalty)

    return {
        "sensor_ok": sensor_ok,
        "warnings": warnings,
        "sensor_confidence": confidence_score,
        "repaired_data": repaired_data
    }