import pandas as pd
import joblib
from sklearn.metrics import classification_report, accuracy_score

model = joblib.load("aletheia_temporal_v4.pkl")

df = pd.read_csv("temporal_dataset_v42_test.csv")

X = df.drop("future_label", axis=1)
y = df["future_label"]

predictions = model.predict(X)

accuracy = accuracy_score(y, predictions)

print(f"Adversarial Test Accuracy: {accuracy*100:.2f}%")
print()
print(classification_report(y, predictions))
