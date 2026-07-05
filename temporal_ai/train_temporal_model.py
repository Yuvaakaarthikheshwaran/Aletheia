import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

df = pd.read_csv("temporal_dataset_v5_merged.csv")

X = df.drop("future_label", axis=1)
y = df["future_label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print(f"V5.1 Model Accuracy: {accuracy*100:.2f}%")
print()
print(classification_report(y_test, predictions))

joblib.dump(model, "aletheia_temporal_v51.pkl")

print("Model saved as aletheia_temporal_v51.pkl")
