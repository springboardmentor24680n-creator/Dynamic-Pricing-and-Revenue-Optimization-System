import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

# Load Dataset
dataset_path = os.path.join("datasets", "products_dataset.csv")
data = pd.read_csv(dataset_path)

# Select Features
X = data[["price", "stock", "units_sold", "competitor_price", "discount"]]

# Target
y = data["target_price"]

# Train Model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

# Save Model
joblib.dump(model, os.path.join("ml", "price_model.pkl"))

print("Model Trained Successfully!")
print("Model saved as ml/price_model.pkl")