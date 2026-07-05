import pandas as pd
import random

data = []

for _ in range(4000):
    scenario = random.choice([
        "stable",
        "future_heat_stress",
        "future_water_stress",
        "future_root_zone_stress"
    ])

    if scenario == "stable":
        base_temp = random.uniform(25, 30)
        base_humidity = random.uniform(60, 80)
        base_soil = random.uniform(60, 80)

        row = {
            "air_temp_prev2": round(base_temp, 1),
            "air_temp_prev1": round(base_temp + random.uniform(-1, 1), 1),
            "air_temp": round(base_temp + random.uniform(-1, 1), 1),

            "humidity_prev2": round(base_humidity, 1),
            "humidity_prev1": round(base_humidity + random.uniform(-3, 3), 1),
            "humidity": round(base_humidity + random.uniform(-3, 3), 1),

            "soil_moisture_prev2": round(base_soil, 1),
            "soil_moisture_prev1": round(base_soil + random.uniform(-2, 2), 1),
            "soil_moisture": round(base_soil + random.uniform(-2, 2), 1),

            "leaf_temp_delta_prev2": round(random.uniform(0, 2), 1),
            "leaf_temp_delta_prev1": round(random.uniform(0, 2), 1),
            "leaf_temp_delta": round(random.uniform(0, 2), 1),

            "future_label": scenario
        }

    elif scenario == "future_heat_stress":
        row = {
            "air_temp_prev2": round(random.uniform(28, 32), 1),
            "air_temp_prev1": round(random.uniform(32, 36), 1),
            "air_temp": round(random.uniform(36, 40), 1),

            "humidity_prev2": round(random.uniform(55, 65), 1),
            "humidity_prev1": round(random.uniform(40, 55), 1),
            "humidity": round(random.uniform(25, 40), 1),

            "soil_moisture_prev2": round(random.uniform(55, 70), 1),
            "soil_moisture_prev1": round(random.uniform(50, 65), 1),
            "soil_moisture": round(random.uniform(45, 60), 1),

            "leaf_temp_delta_prev2": round(random.uniform(1, 3), 1),
            "leaf_temp_delta_prev1": round(random.uniform(3, 5), 1),
            "leaf_temp_delta": round(random.uniform(5, 8), 1),

            "future_label": scenario
        }

    elif scenario == "future_water_stress":
        row = {
            "air_temp_prev2": round(random.uniform(28, 32), 1),
            "air_temp_prev1": round(random.uniform(30, 34), 1),
            "air_temp": round(random.uniform(32, 36), 1),

            "humidity_prev2": round(random.uniform(55, 65), 1),
            "humidity_prev1": round(random.uniform(45, 55), 1),
            "humidity": round(random.uniform(35, 45), 1),

            "soil_moisture_prev2": round(random.uniform(55, 65), 1),
            "soil_moisture_prev1": round(random.uniform(40, 55), 1),
            "soil_moisture": round(random.uniform(20, 40), 1),

            "leaf_temp_delta_prev2": round(random.uniform(1, 2), 1),
            "leaf_temp_delta_prev1": round(random.uniform(2, 4), 1),
            "leaf_temp_delta": round(random.uniform(4, 6), 1),

            "future_label": scenario
        }

    else:
        row = {
            "air_temp_prev2": round(random.uniform(27, 32), 1),
            "air_temp_prev1": round(random.uniform(28, 33), 1),
            "air_temp": round(random.uniform(29, 34), 1),

            "humidity_prev2": round(random.uniform(50, 65), 1),
            "humidity_prev1": round(random.uniform(45, 60), 1),
            "humidity": round(random.uniform(40, 55), 1),

            "soil_moisture_prev2": round(random.uniform(50, 60), 1),
            "soil_moisture_prev1": round(random.uniform(45, 55), 1),
            "soil_moisture": round(random.uniform(40, 50), 1),

            "leaf_temp_delta_prev2": round(random.uniform(1, 3), 1),
            "leaf_temp_delta_prev1": round(random.uniform(2, 4), 1),
            "leaf_temp_delta": round(random.uniform(3, 5), 1),

            "future_label": scenario
        }

    data.append(row)

df = pd.DataFrame(data)
df.to_csv("temporal_dataset_v4.csv", index=False)

print(df.head())
print()
print(df["future_label"].value_counts())
