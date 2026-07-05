import pandas as pd
import random

data = []

def add_noise(x, noise):
    return round(x + random.uniform(-noise, noise), 1)

for _ in range(6000):
    scenario = random.choice([
        "stable",
        "future_heat_stress",
        "future_water_stress",
        "future_root_zone_stress"
    ])

    if scenario == "stable":
        base_temp = random.uniform(27, 35)
        base_humidity = random.uniform(40, 75)
        base_soil = random.uniform(45, 80)
        base_leaf = random.uniform(1, 4)

        row = {
            "air_temp_prev2": add_noise(base_temp, 2),
            "air_temp_prev1": add_noise(base_temp + random.uniform(-1, 1), 2),
            "air_temp": add_noise(base_temp + random.uniform(-1, 1), 2),

            "humidity_prev2": add_noise(base_humidity, 5),
            "humidity_prev1": add_noise(base_humidity + random.uniform(-4, 4), 5),
            "humidity": add_noise(base_humidity + random.uniform(-4, 4), 5),

            "soil_moisture_prev2": add_noise(base_soil, 4),
            "soil_moisture_prev1": add_noise(base_soil + random.uniform(-3, 3), 4),
            "soil_moisture": add_noise(base_soil + random.uniform(-3, 3), 4),

            "leaf_temp_delta_prev2": add_noise(base_leaf, 1),
            "leaf_temp_delta_prev1": add_noise(base_leaf + random.uniform(-1, 1), 1),
            "leaf_temp_delta": add_noise(base_leaf + random.uniform(-1, 1), 1),

            "future_label": scenario
        }

    elif scenario == "future_heat_stress":
        base_temp = random.uniform(31, 39)
        base_humidity = random.uniform(30, 55)
        base_soil = random.uniform(40, 70)
        base_leaf = random.uniform(2, 6)

        row = {
            "air_temp_prev2": add_noise(base_temp - 3, 2),
            "air_temp_prev1": add_noise(base_temp - 1, 2),
            "air_temp": add_noise(base_temp + 2, 2),

            "humidity_prev2": add_noise(base_humidity + 8, 6),
            "humidity_prev1": add_noise(base_humidity + 3, 6),
            "humidity": add_noise(base_humidity - 5, 6),

            "soil_moisture_prev2": add_noise(base_soil, 4),
            "soil_moisture_prev1": add_noise(base_soil - 2, 4),
            "soil_moisture": add_noise(base_soil - 4, 4),

            "leaf_temp_delta_prev2": add_noise(base_leaf, 1),
            "leaf_temp_delta_prev1": add_noise(base_leaf + 1, 1),
            "leaf_temp_delta": add_noise(base_leaf + 2, 1),

            "future_label": scenario
        }

    elif scenario == "future_water_stress":
        base_temp = random.uniform(30, 37)
        base_humidity = random.uniform(30, 60)
        base_soil = random.uniform(25, 55)
        base_leaf = random.uniform(2, 5)

        row = {
            "air_temp_prev2": add_noise(base_temp - 2, 2),
            "air_temp_prev1": add_noise(base_temp, 2),
            "air_temp": add_noise(base_temp + 2, 2),

            "humidity_prev2": add_noise(base_humidity + 5, 6),
            "humidity_prev1": add_noise(base_humidity, 6),
            "humidity": add_noise(base_humidity - 4, 6),

            "soil_moisture_prev2": add_noise(base_soil + 15, 5),
            "soil_moisture_prev1": add_noise(base_soil + 8, 5),
            "soil_moisture": add_noise(base_soil, 5),

            "leaf_temp_delta_prev2": add_noise(base_leaf, 1),
            "leaf_temp_delta_prev1": add_noise(base_leaf + 1, 1),
            "leaf_temp_delta": add_noise(base_leaf + 2, 1),

            "future_label": scenario
        }

    else:
        base_temp = random.uniform(28, 36)
        base_humidity = random.uniform(35, 65)
        base_soil = random.uniform(35, 60)
        base_leaf = random.uniform(2, 5)

        row = {
            "air_temp_prev2": add_noise(base_temp, 2),
            "air_temp_prev1": add_noise(base_temp + 1, 2),
            "air_temp": add_noise(base_temp + 2, 2),

            "humidity_prev2": add_noise(base_humidity, 6),
            "humidity_prev1": add_noise(base_humidity - 2, 6),
            "humidity": add_noise(base_humidity - 4, 6),

            "soil_moisture_prev2": add_noise(base_soil, 4),
            "soil_moisture_prev1": add_noise(base_soil - 3, 4),
            "soil_moisture": add_noise(base_soil - 5, 4),

            "leaf_temp_delta_prev2": add_noise(base_leaf, 1),
            "leaf_temp_delta_prev1": add_noise(base_leaf + 1, 1),
            "leaf_temp_delta": add_noise(base_leaf + 2, 1),

            "future_label": scenario
        }

    data.append(row)

df = pd.DataFrame(data)
df.to_csv("temporal_dataset_v41.csv", index=False)

print(df.head())
print()
print(df["future_label"].value_counts())
