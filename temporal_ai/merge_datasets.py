import pandas as pd

df1 = pd.read_csv("temporal_dataset_v43.csv")
df2 = pd.read_csv("temporal_dataset_v5.csv")

merged = pd.concat([df1, df2], ignore_index=True)
merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)

merged.to_csv("temporal_dataset_v5_merged.csv", index=False)

print("Merged shape:", merged.shape)
print()
print(merged["future_label"].value_counts())