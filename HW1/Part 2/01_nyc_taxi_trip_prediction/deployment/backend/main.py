from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import os

app = FastAPI(title="NYC Taxi Trip Duration Predictor")

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Load the model on startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), "xgboost_model.pkl")
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

class TripFeatures(BaseModel):
    passenger_count: int
    pickup_longitude: float
    pickup_latitude: float
    dropoff_longitude: float
    dropoff_latitude: float
    pickup_datetime: str # ISO format

def haversine(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    AVG_EARTH_RADIUS = 6371  # in km
    lat = lat2 - lat1
    lng = lng2 - lng1
    d = np.sin(lat * 0.5) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(lng * 0.5) ** 2
    h = 2 * AVG_EARTH_RADIUS * np.arcsin(np.sqrt(d))
    return h

@app.post("/predict")
def predict_duration(trip: TripFeatures):
    # Parse datetime
    dt = pd.to_datetime(trip.pickup_datetime)
    hour = dt.hour
    day_of_week = dt.dayofweek
    month = dt.month
    
    # Calculate distance
    distance_km = haversine(trip.pickup_latitude, trip.pickup_longitude, trip.dropoff_latitude, trip.dropoff_longitude)
    
    # Prepare feature DataFrame to match training data structure
    features = pd.DataFrame([{
        'passenger_count': trip.passenger_count,
        'pickup_longitude': trip.pickup_longitude,
        'pickup_latitude': trip.pickup_latitude,
        'dropoff_longitude': trip.dropoff_longitude,
        'dropoff_latitude': trip.dropoff_latitude,
        'hour': hour,
        'day_of_week': day_of_week,
        'month': month,
        'distance_km': distance_km
    }])
    
    # Predict (model outputs log(1+trip_duration))
    log_pred = model.predict(features)[0]
    
    # Convert back to original scale (seconds)
    pred_seconds = np.expm1(log_pred)
    
    # Cap prediction at reasonable bounds (e.g., min 60 seconds)
    pred_seconds = max(60.0, pred_seconds)
    
    return {
        "predicted_duration_seconds": float(pred_seconds),
        "predicted_duration_minutes": float(pred_seconds / 60.0)
    }

@app.get("/api/metrics")
def get_metrics():
    # Return mock/recorded feature importances and metrics for the frontend charts
    return {
        "metrics": {
            "rmse_log": 0.45,
            "rmse_sec": 2310.04,
            "mae_sec": 1953.93,
            "r_squared": 0.72
        },
        "feature_importance": [
            {"feature": "distance_km", "importance": 0.45},
            {"feature": "hour", "importance": 0.22},
            {"feature": "dropoff_longitude", "importance": 0.12},
            {"feature": "dropoff_latitude", "importance": 0.10},
            {"feature": "pickup_longitude", "importance": 0.08},
            {"feature": "pickup_latitude", "importance": 0.03}
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
