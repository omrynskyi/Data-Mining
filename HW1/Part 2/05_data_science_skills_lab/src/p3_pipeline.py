"""CRISP-DM Phase 3 — sklearn-pipelines skill: the reusable preprocessing artifact.

Exposes:
    build_preprocessor() -> unfitted sklearn.pipeline.Pipeline
    FEATURE_SPEC          -> dict describing the raw column roles

The pipeline is:  FeatureEngineer (custom transformer) -> ColumnTransformer
FeatureEngineer does the SAME cleaning/engineering as p3_data_cleaning.py /
p3_feature_engineering.py, but re-implemented as a fit/transform step so it
runs INSIDE cross-validation and INSIDE the saved artifact — this is the
anti-leakage point of the sklearn-pipelines skill: engineering statistics
(here, none are learned — everything is deterministic domain logic) and
encodings must never be computed on data the model will later be scored on.

This module is meant to be imported by later CRISP-DM phases:
    from p3_pipeline import build_preprocessor, FEATURE_SPEC
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ADDON_COLS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
              "TechSupport", "StreamingTV", "StreamingMovies"]
SENTINEL_COLS = ADDON_COLS + ["MultipleLines"]

# Raw columns the pipeline consumes (everything except customerID/Churn).
RAW_NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]
RAW_CATEGORICAL = ["gender", "SeniorCitizen", "Partner", "Dependents", "PhoneService",
                    "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
                    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
                    "Contract", "PaperlessBilling", "PaymentMethod"]

ENGINEERED_NUMERIC = ["avg_monthly_spend", "spend_gap", "num_addon_services", "charges_per_service"]
ENGINEERED_CATEGORICAL = ["tenure_bucket", "has_internet", "is_month_to_month",
                           "is_electronic_check", "is_new_customer"]

FEATURE_SPEC = {
    "drop": ["customerID"],
    "target": "Churn",
    "raw_numeric": RAW_NUMERIC,
    "raw_categorical": RAW_CATEGORICAL,
    "engineered_numeric": ENGINEERED_NUMERIC,
    "engineered_categorical": ENGINEERED_CATEGORICAL,
    "numeric": RAW_NUMERIC + ENGINEERED_NUMERIC,
    "categorical": RAW_CATEGORICAL + ENGINEERED_CATEGORICAL,
}


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Deterministic domain-logic cleaning + feature engineering.

    Fit is a no-op (nothing here is learned from data — every rule is a
    fixed domain fact, e.g. tenure==0 => TotalCharges==0), so applying it
    inside a Pipeline costs nothing but removes any chance of accidentally
    computing a step on train+test combined, and makes the whole chain
    (clean -> engineer -> encode -> scale) a single joblib-serializable
    object for the modeling/serving phases.
    """

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()

        # --- cleaning (mirrors p3_data_cleaning.py) ---
        mask_new = df["tenure"] == 0
        df.loc[mask_new & df["TotalCharges"].isna(), "TotalCharges"] = 0.0
        for c in SENTINEL_COLS:
            sentinel = "No internet service" if c in ADDON_COLS else "No phone service"
            df[c] = df[c].replace(sentinel, "No")

        # --- engineering (mirrors p3_feature_engineering.py) ---
        bins = [-1, 6, 12, 24, 48, 60, 200]
        labels = ["0-6mo", "7-12mo", "13-24mo", "25-48mo", "49-60mo", "61mo+"]
        df["tenure_bucket"] = pd.cut(df["tenure"], bins=bins, labels=labels).astype(str)

        df["avg_monthly_spend"] = np.where(
            df["tenure"] > 0, df["TotalCharges"] / df["tenure"], df["MonthlyCharges"]
        )
        df["spend_gap"] = df["avg_monthly_spend"] - df["MonthlyCharges"]
        df["num_addon_services"] = (df[ADDON_COLS] == "Yes").sum(axis=1)
        df["has_internet"] = (df["InternetService"] != "No").astype(int)
        df["is_month_to_month"] = (df["Contract"] == "Month-to-month").astype(int)
        df["is_electronic_check"] = (df["PaymentMethod"] == "Electronic check").astype(int)

        n_services = (
            (df["PhoneService"] == "Yes").astype(int)
            + df["has_internet"]
            + (df[ADDON_COLS] == "Yes").sum(axis=1)
        ).clip(lower=1)
        df["charges_per_service"] = df["MonthlyCharges"] / n_services
        df["is_new_customer"] = (df["tenure"] <= 3).astype(int)

        return df

    def get_feature_names_out(self, input_features=None):
        return np.array(input_features)


def build_preprocessor() -> Pipeline:
    """Return an UNFITTED Pipeline: FeatureEngineer -> ColumnTransformer.

    numeric:      median impute + StandardScaler
    categorical:  most-frequent impute + OneHotEncoder(handle_unknown='ignore')
    customerID and Churn are simply not selected by the ColumnTransformer
    (drop="passthrough" columns aside), so they fall out of the pipeline
    without needing an explicit drop step.
    """
    numeric_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore")),
    ])
    column_transformer = ColumnTransformer([
        ("num", numeric_pipe, FEATURE_SPEC["numeric"]),
        ("cat", categorical_pipe, FEATURE_SPEC["categorical"]),
    ])
    return Pipeline([
        ("engineer", FeatureEngineer()),
        ("prep", column_transformer),
    ])


if __name__ == "__main__":
    import pathlib
    ROOT = pathlib.Path(__file__).resolve().parents[1]
    train = pd.read_csv(ROOT / "data" / "processed" / "train_clean.csv")
    X = train.drop(columns=["customerID", "Churn"])
    prep = build_preprocessor()
    Xt = prep.fit_transform(X)
    print(f"build_preprocessor() smoke test: input {X.shape} -> output {Xt.shape}")
    names = prep.named_steps["prep"].get_feature_names_out()
    print(f"{len(names)} output features, first 10: {list(names[:10])}")
