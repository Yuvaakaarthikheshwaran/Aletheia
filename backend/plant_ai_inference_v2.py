import copy
from plant_profile_schema import DEFAULT_PROFILE


def infer_plant_profile_v2(plant_name):
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile["plant"] = plant_name

    name = plant_name.lower()

    if "tomato" in name:
        profile["day_profile"] = {
            "air_temp": [21, 27],
            "humidity": [60, 75],
            "soil_moisture": [60, 80],
            "soil_temp": [20, 28],
            "light": [800, 1200],
            "leaf_temp_delta": [2, 5]
        }

        profile["night_profile"] = {
            "air_temp": [16, 18],
            "humidity": [70, 85],
            "soil_moisture": [60, 80],
            "soil_temp": [18, 25],
            "light": [0, 0],
            "leaf_temp_delta": [1, 4]
        }

    return profile