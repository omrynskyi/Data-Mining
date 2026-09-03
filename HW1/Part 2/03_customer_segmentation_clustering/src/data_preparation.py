"""
CRISP-DM Phase 3: Data Preparation, Feature Scaling, and Categorical Encoding.
"""

from typing import Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

from src.config import FEATURE_SETS


class CustomerPreprocessor:
    """Prepares, encodes, and scales customer feature subsets for clustering."""

    def __init__(
        self,
        scaler_type: str = "standard",
        feature_set: str = "2d",
    ):
        self.scaler_type = str(scaler_type).lower().strip()
        self.feature_set_name = str(feature_set).lower().strip()

        if self.feature_set_name not in FEATURE_SETS:
            raise ValueError(
                f"Unknown feature set '{feature_set}'. Must be one of {list(FEATURE_SETS.keys())}"
            )
        self.feature_names: List[str] = FEATURE_SETS[self.feature_set_name]

        if self.scaler_type == "standard":
            self.scaler: Optional[Any] = StandardScaler()
        elif self.scaler_type == "minmax":
            self.scaler = MinMaxScaler()
        elif self.scaler_type == "robust":
            self.scaler = RobustScaler()
        elif self.scaler_type in ["none", "identity", "unscaled"]:
            self.scaler = None
        else:
            raise ValueError(
                f"Unknown scaler type '{scaler_type}'. Choose from 'standard', 'minmax', 'robust', 'none'."
            )

        self.is_fitted: bool = False
        self.active_columns: List[str] = []

    def _prepare_raw_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """Encodes categorical fields and extracts the active feature matrix."""
        df_proc = df.copy()

        # Handle gender encoding if present in feature set
        if "gender" in self.feature_names:
            df_proc["gender_encoded"] = (
                df_proc["gender"]
                .astype(str)
                .str.capitalize()
                .map({"Male": 0.0, "Female": 1.0})
                .fillna(0.0)
            )
            self.active_columns = [
                "gender_encoded" if c == "gender" else c for c in self.feature_names
            ]
        else:
            self.active_columns = list(self.feature_names)

        X_raw = df_proc[self.active_columns].values.astype(float)
        return X_raw, df_proc

    def fit(self, df: pd.DataFrame) -> "CustomerPreprocessor":
        """Fits the scaler on input data."""
        X_raw, _ = self._prepare_raw_matrix(df)
        if self.scaler is not None:
            self.scaler.fit(X_raw)
        self.is_fitted = True
        return self

    def fit_transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """Fits the scaler and returns transformed NumPy matrix along with processed DataFrame."""
        X_raw, df_proc = self._prepare_raw_matrix(df)
        if self.scaler is not None:
            X_scaled = self.scaler.fit_transform(X_raw)
        else:
            X_scaled = X_raw

        self.is_fitted = True
        return X_scaled, df_proc

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms input DataFrame using previously fitted scaler."""
        if not self.is_fitted and self.scaler is not None:
            raise RuntimeError("CustomerPreprocessor must be fitted before calling transform().")
        X_raw, _ = self._prepare_raw_matrix(df)
        return self.scaler.transform(X_raw) if self.scaler is not None else X_raw

    def inverse_transform(self, X_scaled: np.ndarray) -> np.ndarray:
        """Inverts scaled matrix back to original feature space."""
        if self.scaler is not None:
            return self.scaler.inverse_transform(X_scaled)
        return X_scaled


# Alias for backward compatibility
DataPreparation = CustomerPreprocessor
