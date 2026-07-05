def infer_plant_profile(plant_name):
    name = plant_name.lower()

    if "cactus" in name or "succulent" in name:
        return {
            "optimal_air_temp": [25, 40],
            "optimal_humidity": [10, 40],
            "optimal_soil_moisture": [10, 30],
            "optimal_soil_temp": [22, 35],
            "optimal_light": [900, 1500],
            "optimal_leaf_delta": [3, 6]
        }

    if "orchid" in name:
        return {
            "optimal_air_temp": [18, 30],
            "optimal_humidity": [60, 85],
            "optimal_soil_moisture": [40, 60],
            "optimal_soil_temp": [18, 28],
            "optimal_light": [500, 900],
            "optimal_leaf_delta": [2, 5]
        }

    if "banana" in name or "tropical" in name:
        return {
            "optimal_air_temp": [24, 35],
            "optimal_humidity": [60, 90],
            "optimal_soil_moisture": [65, 85],
            "optimal_soil_temp": [24, 32],
            "optimal_light": [900, 1400],
            "optimal_leaf_delta": [2, 5]
        }

    return {
        "optimal_air_temp": [20, 30],
        "optimal_humidity": [40, 70],
        "optimal_soil_moisture": [40, 70],
        "optimal_soil_temp": [20, 30],
        "optimal_light": [700, 1200],
        "optimal_leaf_delta": [2, 5]
    }
