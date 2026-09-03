"""Chunk 17 — Phase 5: error analysis on the (superseded) multiclass model's
grouped-CV OOF predictions.

Reads `final_model_oof_predictions.csv` and `final_model_feature_importance.csv`
(produced by `train_final_model.py`). Superseded by Chunk 18/19's ordinal
model — see `evaluate_ordinal_model.py` for the current model's equivalent
analysis. Kept for the historical record; the shared analysis logic itself
now lives in `helpers/error_analysis.py` so the current model's evaluation
does not depend on this archived script.
"""

from pathlib import Path


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.error_analysis import run_analysis

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OOF_PATH = PROJECT_ROOT / "pipeline" / "results" / "final_model_oof_predictions.csv"
IMPORTANCE_PATH = PROJECT_ROOT / "pipeline" / "results" / "final_model_feature_importance.csv"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "results" / "final_model_error_analysis.json"

if __name__ == "__main__":
    run_analysis(OOF_PATH, IMPORTANCE_PATH, OUTPUT_PATH)
