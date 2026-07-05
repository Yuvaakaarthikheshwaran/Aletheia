import pandas as pd
import random

data = []

def noise(x, n):
    return round(x + random.uniform(-n, n), 1)


for _ in range(8000):
    scenario = random.choices(
        [
            "stable",
            "future_heat_stress",
            "future_water_stress",
            "future_root_zone_stress"
        ],
        weights=[65, 12, 12, 11],
        k=1
    )[0]

    weather = random.choice(["normal", "hot", "cloudy", "humid"])
    greenhouse = random.choice(["stable", "fan_on", "irrigation_on"])

    temp = random.uniform(28, 35)
    humidity = random.uniform(40, 70)
    soil = random.uniform(40, 80)
    leaf = random.uniform(2, 5)

    # Weather effects
    if weather == "hot":
        temp += random.uniform(3, 8)
        humidity -= random.uniform(5, 15)
        leaf += random.uniform(1, 3)

    elif weather == "cloudy":
        temp -= random.uniform(2, 4)
        humidity += random.uniform(5, 10)

    elif weather == "humid":
        humidity += random.uniform(10, 20)

    # Greenhouse actions
    if greenhouse == "fan_on":
        temp -= random.uniform(2, 4)
        humidity += random.uniform(2, 6)

    elif greenhouse == "irrigation_on":
        soil += random.uniform(8, 20)
        humidity += random.uniform(3, 8)

    # Scenario-specific overrides
    if scenario == "future_heat_stress":
        temp += random.uniform(5, 10)
        humidity -= random.uniform(10, 25)
        leaf += random.uniform(2, 5)

    elif scenario == "future_water_stress":
        soil -= random.uniform(20, 35)
        temp += random.uniform(2, 6)
        humidity -= random.uniform(5, 15)
        leaf += random.uniform(1, 4)

    elif scenario == "future_root_zone_stress":
        soil -= random.uniform(8, 20)
        temp += random.uniform(2, 5)
        leaf += random.uniform(1, 3)

    # Sensor faults/noise
    if random.random() < 0.08:
        temp += random.uniform(-6, 6)

    if random.random() < 0.08:
        humidity += random.uniform(-20, 20)

    if random.random() < 0.08:
        soil += random.uniform(-15, 15)

    if random.random() < 0.08:
        leaf += random.uniform(-4, 4)

    row = {
        "air_temp_prev2": noise(temp - random.uniform(0, 3), 2),
        "air_temp_prev1": noise(temp - random.uniform(0, 2), 2),
        "air_temp": noise(temp, 2),

        "humidity_prev2": noise(humidity + random.uniform(-5, 5), 5),
        "humidity_prev1": noise(humidity + random.uniform(-4, 4), 5),
        "humidity": noise(humidity, 5),

        "soil_moisture_prev2": noise(soil + random.uniform(-5, 5), 4),
        "soil_moisture_prev1": noise(soil + random.uniform(-4, 4), 4),
        "soil_moisture": noise(soil, 4),

        "leaf_temp_delta_prev2": noise(leaf + random.uniform(-2, 2), 1),
        "leaf_temp_delta_prev1": noise(leaf + random.uniform(-1, 1), 1),
        "leaf_temp_delta": noise(leaf, 1),

        "future_label": scenario
    }

    data.append(row)

df = pd.DataFrame(data)
df.to_csv("temporal_dataset_v5.csv", index=False)

print(df.head())
print()
print(df["future_label"].value_counts())