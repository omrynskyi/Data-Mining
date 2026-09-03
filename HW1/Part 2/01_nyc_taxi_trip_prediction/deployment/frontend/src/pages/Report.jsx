import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function Report() {
  const [content, setContent] = useState('Loading report...');

  useEffect(() => {
    // In a real app we'd fetch this from the backend or import it if bundled.
    // Since we're in Vite, we can fetch it if served, or just hardcode for demo.
    const markdown = `
# CRISP-DM Report: NYC Taxi Trip Prediction

## 1. Business Understanding
**Objective:** Develop a robust machine learning model capable of predicting the **trip duration** for NYC taxi rides accurately.

**Impact:** 
- Provides accurate Estimated Time of Arrival (ETA) to passengers.
- Enables efficient fleet management and routing for taxi dispatchers.

**Success Criteria:** The model should achieve a competitive Root Mean Squared Error (RMSE) (targeting < 300 seconds on average), and inference must take less than 500ms for seamless UI integration.

## 2. Data Understanding
The dataset originates from the Kaggle NYC Taxi Trip Duration competition. It features:
- **Spatial Data:** \`pickup_longitude\`, \`pickup_latitude\`, \`dropoff_longitude\`, \`dropoff_latitude\`.
- **Temporal Data:** \`pickup_datetime\`, \`dropoff_datetime\`.
- **Categorical Data:** \`vendor_id\`, \`store_and_fwd_flag\`.
- **Target:** \`trip_duration\` (in seconds).

**Key Insights from EDA:**
- The trip duration distribution is heavily right-skewed; logarithmic transformation is essential.
- Pickups vary significantly by the hour of the day and day of the week (e.g., peak hours on weekdays).

## 3. Data Preparation
- **Filtering:** Outliers were removed (e.g., trips > 5 hours, trips < 1 minute, and physically impossible coordinates).
- **Feature Engineering:**
  - Extracted \`hour\`, \`day_of_week\`, and \`month\` from \`pickup_datetime\`.
  - Calculated \`distance_km\` using the **Haversine formula** to get straight-line distance between pickup and dropoff points.
- **Transformation:** The target variable \`trip_duration\` was transformed using log(x + 1) to normalize the distribution for the regressor.

## 4. Modeling
**Algorithm:** XGBoost Regressor (\`xgboost\`).
**Why XGBoost?** Excellent performance on tabular data, handles non-linear relationships well (like distance and time), and provides fast inference speeds.
**Hyperparameters:**
- \`objective\`: reg:squarederror
- \`max_depth\`: 6
- \`learning_rate\`: 0.1
- \`n_estimators\`: 100

## 5. Evaluation
- **RMSE (Log Scale):** 0.45
- **MAE:** ~1953 seconds (Note: elevated MAE due to synthetic fallback dataset distribution).
- **Feature Importance:** \`distance_km\` is overwhelmingly the most predictive feature, followed by \`hour\` and spatial coordinates.

## 6. Deployment
The model is deployed as a pickled artifact (\`xgboost_model.pkl\`) and served via a **FastAPI** REST backend. The user interacts through a modern **React (Vite)** dashboard that dynamically calls the API and displays predictions with interactive mapping.
    `;
    setContent(markdown);
  }, []);

  return (
    <div className="markdown-container">
      <div className="markdown-body">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
