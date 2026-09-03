import kagglehub
import shutil
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_data(dest_dir):
    print("Generating synthetic NYC taxi data as fallback...")
    os.makedirs(dest_dir, exist_ok=True)
    n_samples = 10000
    np.random.seed(42)
    
    # Generate random dates in 2016
    start_date = datetime(2016, 1, 1)
    pickup_datetimes = [start_date + timedelta(days=np.random.randint(0, 180), minutes=np.random.randint(0, 1440)) for _ in range(n_samples)]
    
    # NYC Coordinates bounding box approx
    # Longitude: -74.05 to -73.75, Latitude: 40.60 to 40.90
    pickup_longs = np.random.uniform(-74.05, -73.75, n_samples)
    pickup_lats = np.random.uniform(40.60, 40.90, n_samples)
    
    # Dropoff nearby
    dropoff_longs = pickup_longs + np.random.normal(0, 0.02, n_samples)
    dropoff_lats = pickup_lats + np.random.normal(0, 0.02, n_samples)
    
    # Calculate approx distance to make duration realistic
    def haversine_array(lat1, lng1, lat2, lng2):
        lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
        lat = lat2 - lat1
        lng = lng2 - lng1
        d = np.sin(lat * 0.5) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(lng * 0.5) ** 2
        return 2 * 6371 * np.arcsin(np.sqrt(d))

    dist_km = haversine_array(pickup_lats, pickup_longs, dropoff_lats, dropoff_longs)
    
    # NYC traffic is slow, approx 3-4 mins per km (180-240 seconds)
    # Plus a base pickup time and some noise
    trip_durations = 120 + (dist_km * 200) + np.random.normal(0, 30, n_samples)
    trip_durations = np.clip(trip_durations, 60, 7200).astype(int)
    
    dropoff_datetimes = [p + timedelta(seconds=int(d)) for p, d in zip(pickup_datetimes, trip_durations)]
    
    df = pd.DataFrame({
        'id': [f'id{i}' for i in range(n_samples)],
        'vendor_id': np.random.choice([1, 2], n_samples),
        'pickup_datetime': pickup_datetimes,
        'dropoff_datetime': dropoff_datetimes,
        'passenger_count': np.random.choice([1, 2, 3, 4, 5, 6], n_samples, p=[0.7, 0.15, 0.05, 0.05, 0.03, 0.02]),
        'pickup_longitude': pickup_longs,
        'pickup_latitude': pickup_lats,
        'dropoff_longitude': dropoff_longs,
        'dropoff_latitude': dropoff_lats,
        'store_and_fwd_flag': np.random.choice(['N', 'Y'], n_samples, p=[0.99, 0.01]),
        'trip_duration': trip_durations
    })
    
    df.to_csv(os.path.join(dest_dir, 'train.csv'), index=False)
    print(f"Synthetic data saved to {os.path.join(dest_dir, 'train.csv')}")

dest_dir = "data"
os.makedirs(dest_dir, exist_ok=True)

try:
    print("Attempting to download dataset 'c/nyc-taxi-trip-duration'...")
    path = kagglehub.competition_download("nyc-taxi-trip-duration")
    print("Downloaded to:", path)

    for item in os.listdir(path):
        s = os.path.join(path, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    print(f"Data copied to {os.path.abspath(dest_dir)}")
except Exception as e:
    print(f"Kaggle download failed: {e}")
    print("Please configure kaggle.json to download real data.")
    generate_synthetic_data(dest_dir)
