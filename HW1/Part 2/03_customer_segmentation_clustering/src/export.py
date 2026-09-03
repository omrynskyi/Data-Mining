"""
CRISP-DM Phase 6: Deployment & Artifact Export Module.
Serializes Joblib models, customer segments CSV, metrics JSON, and dashboard JSON payload.
"""

from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from src.config import ARTIFACTS_DIR, DASHBOARD_DATA_DIR, MODELS_DIR

logger = logging.getLogger("pipeline.export")


def sanitize_json(obj: Any) -> Any:
    """
    Recursively converts numpy numbers, arrays, NaN, and Infinity into standard JSON-compliant values.
    """
    if obj is None:
        return None
    elif isinstance(obj, (bool, np.bool_)):
        # Preserve JSON booleans (bool is a subclass of int, so this must come first)
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return round(val, 4)
    elif isinstance(obj, np.ndarray):
        return [sanitize_json(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {str(k): sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_json(x) for x in obj]
    return obj


def compute_feature_quartiles(series: pd.Series) -> Dict[str, float]:
    """Calculates min, Q1, median, Q3, max, mean, std for distribution charts."""
    clean = series.dropna().astype(float)
    if clean.empty:
        return {"min": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}
    return {
        "min": round(float(clean.min()), 2),
        "q1": round(float(clean.quantile(0.25)), 2),
        "median": round(float(clean.median()), 2),
        "q3": round(float(clean.quantile(0.75)), 2),
        "max": round(float(clean.max()), 2),
        "mean": round(float(clean.mean()), 2),
        "std": round(float(clean.std()), 2),
    }


class ArtifactExporter:
    """Serializes pipeline models, metrics, and dashboard payloads."""

    def __init__(
        self,
        artifacts_dir: Optional[Union[str, Path]] = None,
        dashboard_dir: Optional[Union[str, Path]] = None,
    ):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
        self.models_dir = self.artifacts_dir / "models"
        self.dashboard_dir = Path(dashboard_dir) if dashboard_dir else DASHBOARD_DATA_DIR

        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save_joblib_models(self, models: Dict[str, Any]) -> Dict[str, str]:
        """Saves fitted models and transformers into .joblib files."""
        saved_paths: Dict[str, str] = {}
        for name, model_obj in models.items():
            if model_obj is not None:
                file_name = f"{name}_model.joblib" if not name.endswith("_model") and name != "scaler" else f"{name}.joblib"
                target_path = self.models_dir / file_name
                joblib.dump(model_obj, target_path)
                saved_paths[name] = str(target_path)
                logger.info(f"Saved model '{name}' to {target_path}")
        return saved_paths

    def export_customer_segments_csv(
        self,
        df_segmented: pd.DataFrame,
        filename: str = "customer_segments.csv",
    ) -> Path:
        """Exports tabular CSV containing customer records with cluster IDs, personas, and PCA coordinates."""
        output_path = self.artifacts_dir / filename
        df_segmented.to_csv(output_path, index=False)
        logger.info(f"Exported customer segments CSV to {output_path} ({len(df_segmented)} rows)")
        return output_path

    def export_metrics_json(
        self,
        metrics_payload: Dict[str, Any],
        filename: str = "metrics.json",
    ) -> Path:
        """Exports evaluation metrics and k-sweep results to artifacts/metrics.json."""
        output_path = self.artifacts_dir / filename
        clean_payload = sanitize_json(metrics_payload)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        logger.info(f"Exported metrics JSON to {output_path}")
        return output_path

    def export_pipeline_output_json(
        self,
        payload: Dict[str, Any],
        export_to_dashboard: bool = True,
    ) -> Path:
        """Exports structured JSON payload adhering to the React dashboard contract."""
        output_path = self.artifacts_dir / "pipeline_output.json"
        clean_payload = sanitize_json(payload)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        logger.info(f"Exported pipeline output JSON to {output_path}")

        if export_to_dashboard and self.dashboard_dir:
            try:
                self.dashboard_dir.mkdir(parents=True, exist_ok=True)
                dashboard_file = self.dashboard_dir / "pipeline_output.json"
                with open(dashboard_file, "w", encoding="utf-8") as f:
                    json.dump(clean_payload, f, indent=2)
                logger.info(f"Successfully synchronized dashboard data to {dashboard_file}")
            except Exception as e:
                logger.warning(f"Could not sync to dashboard directory ({e}), skipping dashboard copy.")

        return output_path
