"""Chunk 19 — Phase 5 refresh: error analysis for the ordinal-regression model.

Runs the identical confusion-matrix / directional-error / cohort-slice /
feature-importance-by-family analysis as the archived `evaluate_final_model.py`
(Chunk 17) — shared via `helpers/error_analysis.py` — but against the new
best model from Chunk 18 (CatBoostRegressor + optimized-threshold decoding),
so Phase 5 reflects the current best model rather than the superseded
multiclass one. `predicted_class` in `ordinal_model_oof_predictions.csv` is
the optimized-threshold decoding (the adopted one, not naive rounding).
"""

from pathlib import Path

from helpers.error_analysis import run_analysis

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OOF_PATH = PROJECT_ROOT / "pipeline" / "results" / "ordinal_model_oof_predictions.csv"
IMPORTANCE_PATH = PROJECT_ROOT / "pipeline" / "results" / "ordinal_model_feature_importance.csv"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "results" / "ordinal_model_error_analysis.json"

if __name__ == "__main__":
    run_analysis(OOF_PATH, IMPORTANCE_PATH, OUTPUT_PATH)
