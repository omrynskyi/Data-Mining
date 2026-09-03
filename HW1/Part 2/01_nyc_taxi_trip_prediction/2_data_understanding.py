import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def run_eda():
    print("Running EDA...")
    os.makedirs('eda', exist_ok=True)
    
    try:
        df = pd.read_csv('data/train.csv')
    except Exception as e:
        print("Data not found. Run download_data.py first.")
        return
        
    print(df.info())
    
    # 1. Distribution of Trip Duration
    plt.figure(figsize=(10, 6))
    sns.histplot(df['trip_duration'], bins=100, kde=True, log_scale=True)
    plt.title('Distribution of Trip Duration (Log Scale)')
    plt.xlabel('Trip Duration (seconds)')
    plt.ylabel('Count')
    plt.savefig('eda/trip_duration_distribution.png')
    plt.close()
    
    # 2. Pickups over days of the week
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
    df['day_of_week'] = df['pickup_datetime'].dt.dayofweek
    plt.figure(figsize=(10, 6))
    sns.countplot(x='day_of_week', data=df)
    plt.title('Pickups by Day of Week')
    plt.xlabel('Day of Week (0=Mon, 6=Sun)')
    plt.ylabel('Count')
    plt.savefig('eda/pickups_by_day.png')
    plt.close()
    
    print("EDA completed. Plots saved to eda/")

if __name__ == "__main__":
    run_eda()
