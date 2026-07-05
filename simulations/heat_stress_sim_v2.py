import pandas as pd
import joblib
import matplotlib.pyplot as plt

# Load model
model = joblib.load("../ai/aletheia_model_v2.pkl")

# Simulated day progression
data = pd.DataFrame({
    "time": ["8 AM", "10 AM", "12 PM", "2 PM", "4 PM"],
    "air_temp": [28, 31, 35, 40, 43],
    "humidity": [72, 62, 48, 30, 24],
    "light": [300, 500, 700, 900, 980],
    "leaf_temp": [29, 32, 39, 46, 50],
    "soil_moisture": [72, 70, 66, 58, 52],
    "soil_temp": [24, 27, 31, 37, 40]
})

# Derived feature
data["leaf_temp_delta"] = data["leaf_temp"] - data["air_temp"]

# Features
X = data[
    [
        "air_temp",
        "humidity",
        "light",
        "leaf_temp",
        "leaf_temp_delta",
        "soil_moisture",
        "soil_temp"
    ]
]

# Predict
predictions = model.predict(X)
data["prediction"] = predictions

print(data)

# Plot
plt.figure(figsize=(10, 5))
plt.plot(data["time"], data["air_temp"], marker="o", label="Air Temp")
plt.plot(data["time"], data["leaf_temp"], marker="o", label="Leaf Temp")

plt.title("Aletheia V2 Heat Stress Simulation")
plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.legend()
plt.grid()

plt.show()
