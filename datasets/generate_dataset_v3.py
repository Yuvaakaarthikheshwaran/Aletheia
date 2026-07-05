
import random
import csv

data = []

def generate_healthy():
    air = random.uniform(24, 32)
    leaf = air + random.uniform(0, 2)
    humidity = random.uniform(50, 80)

    return [
        air,
        humidity,
        random.uniform(300, 700),
        leaf,
        leaf - air,
        random.uniform(55, 85),
        random.uniform(22, 30),
        random.uniform(-1, 1),   # air temp rate
        random.uniform(-3, 3),   # humidity rate
        random.uniform(-1, 1),   # leaf temp rate
        "healthy"
    ]

def generate_heat_stress():
    air = random.uniform(35, 45)
    leaf = air + random.uniform(4, 8)
    humidity = random.uniform(20, 45)

    return [
        air,
        humidity,
        random.uniform(700, 1000),
        leaf,
        leaf - air,
        random.uniform(40, 75),
        random.uniform(30, 40),
        random.uniform(2, 6),
        random.uniform(-15, -5),
        random.uniform(3, 8),
        "heat_stress"
    ]

def generate_water_stress():
    air = random.uniform(30, 40)
    leaf = air + random.uniform(3, 6)
    humidity = random.uniform(25, 55)

    return [
        air,
        humidity,
        random.uniform(500, 900),
        leaf,
        leaf - air,
        random.uniform(10, 35),
        random.uniform(28, 36),
        random.uniform(1, 4),
        random.uniform(-10, -3),
        random.uniform(2, 6),
        "water_stress"
    ]

def generate_root_zone_stress():
    air = random.uniform(28, 38)
    leaf = air + random.uniform(2, 5)
    humidity = random.uniform(40, 70)

    return [
        air,
        humidity,
        random.uniform(400, 800),
        leaf,
        leaf - air,
        random.uniform(70, 95),
        random.uniform(35, 45),
        random.uniform(0, 3),
        random.uniform(-5, 3),
        random.uniform(1, 4),
        "root_zone_stress"
    ]

def generate_nutrient_lockout():
    air = random.uniform(26, 36)
    leaf = air + random.uniform(1, 4)
    humidity = random.uniform(40, 70)

    return [
        air,
        humidity,
        random.uniform(350, 700),
        leaf,
        leaf - air,
        random.uniform(45, 80),
        random.uniform(24, 34),
        random.uniform(-1, 2),
        random.uniform(-4, 2),
        random.uniform(0, 3),
        "nutrient_lockout"
    ]

for _ in range(500):
    data.append(generate_healthy())
    data.append(generate_heat_stress())
    data.append(generate_water_stress())
    data.append(generate_root_zone_stress())
    data.append(generate_nutrient_lockout())

with open("plant_dataset_v3.csv", "w", newline="") as f:
    writer = csv.writer(f)

    writer.writerow([
        "air_temp",
        "humidity",
        "light",
        "leaf_temp",
        "leaf_temp_delta",
        "soil_moisture",
        "soil_temp",
        "air_temp_rate",
        "humidity_rate",
        "leaf_temp_rate",
        "label"
    ])

    writer.writerows(data)

print("V3 dataset generated successfully!")
print(f"Total rows: {len(data)}")