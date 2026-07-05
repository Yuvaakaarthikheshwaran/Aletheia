def parse_range(value):
    value = value.replace("C", "").replace("%", "")
    parts = value.split("-")
    return [int(parts[0]), int(parts[1])]


def generate_plant_profile(raw_data):
    if raw_data is None:
        return None

    profile = {
        "optimal_air_temp": parse_range(raw_data["temperature"]),
        "optimal_humidity": parse_range(raw_data["humidity"]),
        "optimal_soil_moisture": parse_range(raw_data["soil_moisture"]),
        "optimal_soil_temp": parse_range(raw_data["soil_temp"]),
        "optimal_light": parse_range(raw_data["light"]),
        "optimal_leaf_delta": [2, 5]
    }

    return profile
