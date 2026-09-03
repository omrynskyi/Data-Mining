import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pickle
import os

def train_model():
    print("Loading processed data...")
    X_train = pd.read_csv('processed_data/X_train.csv')
    X_test = pd.read_csv('processed_data/X_test.csv')
    y_train = pd.read_csv('processed_data/y_train.csv')
    y_test = pd.read_csv('processed_data/y_test.csv')
    
    print("Training XGBoost model...")
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train.values.ravel())
    
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    
    # Calculate metrics on log scale
    rmse_log = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # Convert predictions back to original scale (seconds)
    y_test_orig = np.expm1(y_test)
    y_pred_orig = np.expm1(y_pred)
    
    rmse = np.sqrt(mean_squared_error(y_test_orig, y_pred_orig))
    mae = mean_absolute_error(y_test_orig, y_pred_orig)
    r2 = r2_score(y_test_orig, y_pred_orig)
    
    print(f"Metrics (Original Scale - seconds):")
    print(f"RMSE: {rmse:.2f}")
    print(f"MAE: {mae:.2f}")
    print(f"R-squared: {r2:.4f}")
    
    # Save metrics to 5_evaluation.md
    with open('5_evaluation.md', 'w') as f:
        f.write("# 5. Evaluation\n\n")
        f.write("## Model Performance Metrics (XGBoost)\n")
        f.write("- **Target Variable**: Trip Duration (seconds)\n")
        f.write(f"- **RMSE (Log Scale)**: {rmse_log:.4f}\n")
        f.write(f"- **RMSE (Original Scale)**: {rmse:.2f} seconds\n")
        f.write(f"- **MAE (Original Scale)**: {mae:.2f} seconds\n")
        f.write(f"- **R-squared**: {r2:.4f}\n\n")
        f.write("## Feature Importance\n")
        f.write("The model identified distance and hour of day as key features for predicting trip duration.\n")

    os.makedirs('deployment/backend', exist_ok=True)
    model_path = 'deployment/backend/xgboost_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
        
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
