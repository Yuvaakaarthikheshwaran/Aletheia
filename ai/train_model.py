import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load dataset
df = pd.read_csv("../datasets/plant_dataset.csv")

# Features (inputs)
X = df[[
    "air_temp",
    "humidity",
    "soil_moisture",
    "light",
    "leaf_temp"
]]

# Labels (output)
y = df["label"]

# Split data into training and testing
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

# Create model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

# Train model
model.fit(X_train, y_train)

# Predictions
y_pred = model.predict(X_test)

# Accuracy
accuracy = accuracy_score(y_test, y_pred)

print(f"Model Accuracy: {accuracy * 100:.2f}%")
print()
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, "aletheia_model.pkl")

print()
print("Model saved as aletheia_model.pkl")
