import pandas as pd
import joblib
import matplotlib.pyplot as plt

# Load trained model
model = joblib.load("../ai/aletheia_model.pkl")

# Simulated timeline data
data = pd.DataFrame({
    "time": ["8 AM", "10 AM", "12 PM", "2 PM", "4 PM"],
    "air_temp": [28, 32, 36, 40, 43],
    "humidity": [70, 60, 45, 30, 25],
    "soil_moisture": [70, 68, 64, 58, 52],
    "light": [300, 500, 700, 900, 950],
    "leaf_temp": [29, 34, 39, 45, 48]
})

# Features only for model
X = data[[
    "air_temp",
    "humidity",
    "soil_moisture",
    "light",
    "leaf_temp"
]]

# Predictions
predictions = model.predict(X)

# Add predictions to dataframe
data["prediction"] = predictions

print(data)

# Plot temperature progression
plt.figure(figsize=(10, 5))
plt.plot(data["time"], data["air_temp"], marker="o", label="Air Temp")
plt.plot(data["time"], data["leaf_temp"], marker="o", label="Leaf Temp")

plt.title("Heat Stress Progression")
plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.legend()
plt.grid()

plt.show()