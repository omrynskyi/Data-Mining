# 1. Business Understanding

## Project Overview
The objective of this project is to develop a machine learning model capable of predicting the **trip duration** for NYC taxi rides. We will follow the **CRISP-DM** (Cross-Industry Standard Process for Data Mining) methodology to ensure a structured approach from data ingestion to model deployment.

## Business Objectives
1. **Accurate ETA Predictions**: Provide an accurate Estimate Time of Arrival (ETA) based on pickup and dropoff locations and the time of the request.
2. **Operational Efficiency**: Help taxi drivers and ride-sharing platforms allocate resources more effectively.
3. **User Experience**: Present the prediction through a beautiful, dynamic, and responsive Vite+React web application to "wow" the users.

## Data Mining Goals
- Download and explore the NYC Taxi Trip Duration dataset.
- Clean and prepare the data (e.g., handling missing values, calculating Haversine distance, extracting datetime features).
- Train an optimized **XGBoost** model to predict `trip_duration`.
- Deploy the model using a **FastAPI** backend and integrate it with the Vite frontend.

## Success Criteria
- **Model Performance**: Achieve a competitive Root Mean Squared Error (RMSE) on the validation set.
- **System Stability**: The FastAPI backend must consistently serve predictions in < 500ms.
- **Frontend Aesthetics**: The web app must feature modern UI/UX with smooth micro-animations, glassmorphism, and responsive layout.
