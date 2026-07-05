import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load dataset
df = pd.read_csv("../datasets/plant_dataset_v3.csv")

# Features
X = df[
    [
        "air_temp",
        "humidity",
        "light",
        "leaf_temp",
        "leaf_temp_delta",
        "soil_moisture",
        "soil_temp",
        "air_temp_rate",
        "humidity_rate",
        "leaf_temp_rate"
    ]
]

# Labels
y = df["label"]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

# Model
model = RandomForestClassifier(
    n_estimators=250,
    random_state=42
)

# Train
model.fit(X_train, y_train)

# Predict
y_pred = model.predict(X_test)

# Evaluate
accuracy = accuracy_score(y_test, y_pred)

print(f"V3 Model Accuracy: {accuracy * 100:.2f}%")
print()
print(classification_report(y_test, y_pred))

# Save
joblib.dump(model, "aletheia_model_v3.pkl")

print()
print("Model saved as aletheia_model_v3.pkl")
