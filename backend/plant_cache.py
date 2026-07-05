import json
import os

CACHE_FILE = "plant_cache.json"


def load_cache():
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w") as f:
            json.dump({}, f)

    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def save_cache(cache_data):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=4)


def get_cached_plant(plant_name):
    cache = load_cache()
    plant_name = plant_name.lower()

    if plant_name in cache:
        return cache[plant_name]

    return None


def store_plant(plant_name, profile):
    cache = load_cache()
    cache[plant_name.lower()] = profile
    save_cache(cache)
