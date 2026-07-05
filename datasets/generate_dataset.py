import random
import csv

data = []

def generate_healthy():
    return [
        random.uniform(24, 32),   # air_temp
        random.uniform(50, 80),   # humidity
        random.uniform(55, 85),   # soil_moisture
        random.uniform(300, 700), # light
        random.uniform(24, 33),   # leaf_temp
        "healthy"
    ]

def generate_heat_stress():
    air = random.uniform(35, 45)
    return [
        air,
        random.uniform(20, 45),
        random.uniform(35, 70),
        random.uniform(700, 1000),
        air + random.uniform(2, 6),
        "heat_stress"
    ]

def generate_nutrient_deficiency():
    air = random.uniform(24, 34)
    return [
        air,
        random.uniform(40, 70),
        random.uniform(50, 80),
        random.uniform(300, 700),
        air + random.uniform(1, 3),
        "nutrient_deficiency"
    ]

def generate_disease_risk():
    air = random.uniform(24, 35)
    return [
        air,
        random.uniform(60, 90),
        random.uniform(50, 80),
        random.uniform(300, 700),
        air + random.uniform(2, 5),
        "disease_risk"
    ]

def generate_root_dysfunction():
    air = random.uniform(25, 35)
    return [
        air,
        random.uniform(40, 75),
        random.uniform(60, 95),
        random.uniform(300, 700),
        air + random.uniform(2, 4),
        "root_dysfunction"
    ]

for _ in range(500):
    data.append(generate_healthy())
    data.append(generate_heat_stress())
    data.append(generate_nutrient_deficiency())
    data.append(generate_disease_risk())
    data.append(generate_root_dysfunction())

with open("plant_dataset.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "air_temp",
        "humidity",
        "soil_moisture",
        "light",
        "leaf_temp",
        "label"
    ])
    writer.writerows(data)

print("Dataset generated successfully!")
print(f"Total rows: {len(data)}")