import re


def extract_range(text, pattern):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return [int(match.group(1)), int(match.group(2))]
    return None


def parse_plant_data(plant_name, tavily_results):
    text = ""

    for result in tavily_results.get("results", []):
        text += result.get("content", "") + " "

    day_temp = extract_range(text, r'(\d+)\s*(?:-|to|–)\s*(\d+)\s*°?C')
    humidity = extract_range(text, r'(\d+)\s*(?:-|to|–)\s*(\d+)\s*%')

    confidence = 0
    if day_temp:
        confidence += 50
    if humidity:
        confidence += 30

    day_profile = {
        "air_temp": day_temp or [20, 30],
        "humidity": humidity or [50, 70],
        "soil_moisture": [40, 75],
        "soil_temp": [20, 30],
        "light": [700, 1200],
        "leaf_temp_delta": [2, 5]
    }

    night_profile = {
        "air_temp": [16, 24],
        "humidity": [60, 85],
        "soil_moisture": [40, 75],
        "soil_temp": [18, 28],
        "light": [0, 0],
        "leaf_temp_delta": [1, 4]
    }

    growth_stages = {
        "germination": {
            "air_temp": [22, 28],
            "humidity": [70, 85],
            "soil_moisture": [65, 85],
            "soil_temp": [22, 28],
            "light": [300, 700],
            "leaf_temp_delta": [1, 3]
        },
        "seedling": {
            "air_temp": [20, 25],
            "humidity": [65, 80],
            "soil_moisture": [60, 80],
            "soil_temp": [20, 26],
            "light": [500, 900],
            "leaf_temp_delta": [2, 4]
        },
        "vegetative": {
            "air_temp": day_profile["air_temp"],
            "humidity": day_profile["humidity"],
            "soil_moisture": [55, 80],
            "soil_temp": [20, 28],
            "light": [700, 1200],
            "leaf_temp_delta": [2, 5]
        },
        "flowering": {
            "air_temp": [
                max(day_profile["air_temp"][0] - 1, 0),
                day_profile["air_temp"][1]
            ],
            "humidity": [
                max(day_profile["humidity"][0] - 5, 0),
                day_profile["humidity"][1]
            ],
            "soil_moisture": [55, 75],
            "soil_temp": [20, 27],
            "light": [800, 1300],
            "leaf_temp_delta": [2, 5]
        },
        "fruiting": {
            "air_temp": day_profile["air_temp"],
            "humidity": day_profile["humidity"],
            "soil_moisture": [60, 80],
            "soil_temp": [20, 28],
            "light": [800, 1300],
            "leaf_temp_delta": [2, 5]
        }
    }

    profile = {
        "plant": plant_name,
        "day_profile": day_profile,
        "night_profile": night_profile,
        "growth_stages": growth_stages,
        "stress_thresholds": {
            "heat_stress": 35,
            "severe_heat_stress": 40,
            "cold_stress": 12,
            "drought_stress": 30,
            "waterlogging_stress": 90
        }
    }

    return profile, confidence