import pandas as pd
import random

data = []

def add_noise(x, noise):
    return round(x + random.uniform(-noise, noise), 1)

for _ in range(2000):
    scenario = random.choice([
        "stable_noon_spike",
        "sensor_noise",
        "recovery_state",
        "mixed_stress",
        "borderline"
    ])

    if scenario == "stable_noon_spike":
        row = {
            "air_temp_prev2": add_noise(30, 3),
            "air_temp_prev1": add_noise(35, 3),
            "air_temp": add_noise(38, 3),

            "humidity_prev2": add_noise(60, 8),
            "humidity_prev1": add_noise(45, 8),
            "humidity": add_noise(35, 8),

            "soil_moisture_prev2": add_noise(75, 5),
            "soil_moisture_prev1": add_noise(74, 5),
            "soil_moisture": add_noise(73, 5),

            "leaf_temp_delta_prev2": add_noise(2, 1),
            "leaf_temp_delta_prev1": add_noise(3, 1),
            "leaf_temp_delta": add_noise(4, 1),

            "future_label": "stable"
        }

    elif scenario == "sensor_noise":
        row = {
            "air_temp_prev2": add_noise(31, 6),
            "air_temp_prev1": add_noise(29, 6),
            "air_temp": add_noise(34, 6),

            "humidity_prev2": add_noise(52, 12),
            "humidity_prev1": add_noise(49, 12),
            "humidity": add_noise(45, 12),

            "soil_moisture_prev2": add_noise(58, 10),
            "soil_moisture_prev1": add_noise(60, 10),
            "soil_moisture": add_noise(57, 10),

            "leaf_temp_delta_prev2": add_noise(3, 2),
            "leaf_temp_delta_prev1": add_noise(2, 2),
            "leaf_temp_delta": add_noise(4, 2),

            "future_label": "stable"
        }

    elif scenario == "recovery_state":
        row = {
            "air_temp_prev2": add_noise(38, 3),
            "air_temp_prev1": add_noise(34, 3),
            "air_temp": add_noise(30, 3),

            "humidity_prev2": add_noise(30, 8),
            "humidity_prev1": add_noise(45, 8),
            "humidity": add_noise(60, 8),

            "soil_moisture_prev2": add_noise(35, 6),
            "soil_moisture_prev1": add_noise(48, 6),
            "soil_moisture": add_noise(65, 6),

            "leaf_temp_delta_prev2": add_noise(7, 2),
            "leaf_temp_delta_prev1": add_noise(4, 2),
            "leaf_temp_delta": add_noise(2, 2),

            "future_label": "stable"
        }

    elif scenario == "mixed_stress":
        row = {
            "air_temp_prev2": add_noise(31, 3),
            "air_temp_prev1": add_noise(35, 3),
            "air_temp": add_noise(39, 3),

            "humidity_prev2": add_noise(55, 8),
            "humidity_prev1": add_noise(42, 8),
            "humidity": add_noise(28, 8),

            "soil_moisture_prev2": add_noise(45, 6),
            "soil_moisture_prev1": add_noise(38, 6),
            "soil_moisture": add_noise(28, 6),

            "leaf_temp_delta_prev2": add_noise(3, 1),
            "leaf_temp_delta_prev1": add_noise(5, 1),
            "leaf_temp_delta": add_noise(7, 1),

            "future_label": "future_water_stress"
        }

    else:
        row = {
            "air_temp_prev2": add_noise(32, 3),
            "air_temp_prev1": add_noise(34, 3),
            "air_temp": add_noise(36, 3),

            "humidity_prev2": add_noise(48, 8),
            "humidity_prev1": add_noise(42, 8),
            "humidity": add_noise(38, 8),

            "soil_moisture_prev2": add_noise(46, 5),
            "soil_moisture_prev1": add_noise(43, 5),
            "soil_moisture": add_noise(40, 5),

            "leaf_temp_delta_prev2": add_noise(3, 1),
            "leaf_temp_delta_prev1": add_noise(4, 1),
            "leaf_temp_delta": add_noise(5, 1),

            "future_label": random.choice([
                "stable",
                "future_heat_stress",
                "future_root_zone_stress"
            ])
        }

    data.append(row)

df = pd.DataFrame(data)
df.to_csv("temporal_dataset_v42_test.csv", index=False)

print(df.head())
print()
print(df["future_label"].value_counts())
