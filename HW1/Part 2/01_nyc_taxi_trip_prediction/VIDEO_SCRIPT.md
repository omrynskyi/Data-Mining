Project 01: NYC Taxi Trip Duration Prediction

WHAT IT IS
An end to end machine learning pipeline that predicts how long a NYC taxi trip will take. Follows the CRISP-DM process: prepare the data, engineer features, train an XGBoost model, then serve predictions through a web app.

HOW TO RUN
Command: make 01   (or ./run --01)
Backend (FastAPI): http://localhost:8000
Frontend (map UI): http://localhost:5173

FILES TO SHOW ON SCREEN
1. 3_data_preparation.py - turns coordinates and timestamps into features
2. 4_modeling.py - trains the XGBoost model and evaluates it
3. deployment/backend/main.py - serves live predictions over an API

CODE - 3_data_preparation.py (distance feature)

def haversine_array(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    AVG_EARTH_RADIUS = 6371  # in km
    lat = lat2 - lat1
    lng = lng2 - lng1
    d = np.sin(lat * 0.5) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(lng * 0.5) ** 2
    h = 2 * AVG_EARTH_RADIUS * np.arcsin(np.sqrt(d))
    return h

df['distance_km'] = haversine_array(
    df['pickup_latitude'].values, df['pickup_longitude'].values,
    df['dropoff_latitude'].values, df['dropoff_longitude'].values,
)

This turns raw pickup and dropoff coordinates into a straight-line distance in kilometers, plus hour of day, day of week, and month are pulled from the timestamp.

CODE - 4_modeling.py (train and evaluate)

model = xgb.XGBRegressor(
    objective='reg:squarederror',
    n_estimators=100,
    learning_rate=0.1,
    max_depth=6,
    random_state=42,
)
model.fit(X_train, y_train.values.ravel())

y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(np.expm1(y_test), np.expm1(y_pred)))
r2 = r2_score(np.expm1(y_test), np.expm1(y_pred))

The target was trained on a log scale, so predictions are converted back to seconds with expm1 before computing RMSE and R-squared.

CODE - deployment/backend/main.py (live prediction endpoint)

@app.post("/predict")
def predict_duration(trip: TripFeatures):
    dt = pd.to_datetime(trip.pickup_datetime)
    hour, day_of_week, month = dt.hour, dt.dayofweek, dt.month
    distance_km = haversine(trip.pickup_latitude, trip.pickup_longitude,
                             trip.dropoff_latitude, trip.dropoff_longitude)
    features = pd.DataFrame([{ 'passenger_count': trip.passenger_count, ... }])

SCRIPT

Intro, 0:00 to 0:25
Say you are showing Project 01, NYC taxi trip duration prediction.
Launch it with make 01.
Mention the Makefile checks that the FastAPI backend is running on port 8000 before it opens the frontend.

Code walkthrough, 0:25 to 1:15
Open 3_data_preparation.py, show the haversine function, explain it converts raw coordinates into a distance feature, plus hour, day of week, and month.
Open 4_modeling.py, show the XGBoost regressor being trained on a log transformed target, then converted back to seconds for evaluation. Mention the validation RMSE is about 33 seconds.
Optionally open deployment/backend/main.py and point out the predict endpoint reuses the exact same feature logic at inference time.

Live demo, 1:15 to 2:00
Switch to the browser at localhost 5173.
Click a pickup point and a dropoff point on the map.
Submit the request and show the predicted trip duration, distance, and any model stats displayed.
Explain that the browser sends a JSON payload to POST /predict on the FastAPI backend, and the model returns a prediction in real time.

Wrap up
This concludes Project 01.
