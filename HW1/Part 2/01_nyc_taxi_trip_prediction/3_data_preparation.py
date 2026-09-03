import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
import zipfile

def prepare_data():
    print("Loading data...")
    data_dir = 'data'
    train_zip = os.path.join(data_dir, 'train.zip')
    
    if os.path.exists(train_zip):
        print("Extracting train.zip...")
        with zipfile.ZipFile(train_zip, 'r') as zip_ref:
            zip_ref.extractall(data_dir)
            
    train_file = os.path.join(data_dir, 'train.csv')
    if not os.path.exists(train_file):
        print(f"Error: {train_file} not found. Ensure the dataset downloaded correctly.")
        return
        
    df = pd.read_csv(train_file)
    print(f"Loaded {len(df)} records.")
    
    # Take a sample to speed up training
    sample_size = min(len(df), 100000)
    df = df.sample(n=sample_size, random_state=42)
    
    print("Cleaning and preparing data...")
    # Basic cleaning
    df = df[df['trip_duration'] < 3600 * 5] # Remove trips > 5 hours
    df = df[df['trip_duration'] > 60] # Remove trips < 1 min
    
    # Datetime features
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
    df['hour'] = df['pickup_datetime'].dt.hour
    df['day_of_week'] = df['pickup_datetime'].dt.dayofweek
    df['month'] = df['pickup_datetime'].dt.month
    
    # Haversine distance
    def haversine_array(lat1, lng1, lat2, lng2):
        lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
        AVG_EARTH_RADIUS = 6371  # in km
        lat = lat2 - lat1
        lng = lng2 - lng1
        d = np.sin(lat * 0.5) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(lng * 0.5) ** 2
        h = 2 * AVG_EARTH_RADIUS * np.arcsin(np.sqrt(d))
        return h

    df['distance_km'] = haversine_array(df['pickup_latitude'].values, 
                                        df['pickup_longitude'].values, 
                                        df['dropoff_latitude'].values, 
                                        df['dropoff_longitude'].values)
    
    features = ['passenger_count', 'pickup_longitude', 'pickup_latitude', 
                'dropoff_longitude', 'dropoff_latitude', 'hour', 'day_of_week', 'month', 'distance_km']
    target = 'trip_duration'
    
    X = df[features]
    y = np.log1p(df[target]) # Log transform the target
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    os.makedirs('processed_data', exist_ok=True)
    X_train.to_csv('processed_data/X_train.csv', index=False)
    X_test.to_csv('processed_data/X_test.csv', index=False)
    y_train.to_csv('processed_data/y_train.csv', index=False)
    y_test.to_csv('processed_data/y_test.csv', index=False)
    print("Data preparation complete. Saved to 'processed_data/'")

if __name__ == "__main__":
    prepare_data()
