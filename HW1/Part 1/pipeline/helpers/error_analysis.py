"""Shared error-analysis logic (Chunk 17), reused by both the archived
multiclass model's evaluation and the current final (ordinal) model's
evaluation — moved here so the current model's evaluation script doesn't
depend on the archived one.

Reports, from a model's grouped-CV out-of-fold predictions:

1. Confusion matrix + per-class precision/recall/F1 (grouped CV = the
   realistic, out-of-sample estimate used throughout Phases 4-5).
2. A directional-error check: does the model systematically over- or
   under-predict adoption speed for any true class?
3. Cohort error slices (pet type, age bucket, photo availability, fee,
   rescuer listing-count bucket) with QWK/MAE/accuracy and sample sizes,
   flagging small-n cohorts per the Phase 1/2 caution against definitive
   claims from thin groups.
4. Feature importance aggregated to the feature-family level, so
   interpretability claims are made about "families," not 512 individual
   PCA/TF-IDF dimensions.

No model is fit or tuned here; this is read-only analysis of already-produced
out-of-fold predictions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, cohen_kappa_score, confusion_matrix, mean_absolute_error

from helpers.fold_safe_features import CATEGORICAL_COLUMNS, FEATURE_GROUPS, TARGET_COLUMN

SMALL_N_THRESHOLD = 100


def cohort_score(sub: pd.DataFrame) -> dict:
    y_true = sub[TARGET_COLUMN].to_numpy()
    y_pred = sub["predicted_class"].to_numpy()
    return {
        "n": int(len(sub)),
        "small_n_caution": bool(len(sub) < SMALL_N_THRESHOLD),
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")) if len(sub) > 1 else None,
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def feature_family(name: str) -> str:
    if name in CATEGORICAL_COLUMNS:
        return "categorical"
    for group in ("core_numeric", "text_shape", "sentiment", "vision_metadata", "image_pixels"):
        if name in FEATURE_GROUPS[group]:
            return group
    if name.startswith("text_svd_"):
        return "text_tfidf_svd"
    if name.startswith("img_emb_pca_") or name == "img_embedding_available":
        return "frozen_image_embedding"
    return "unknown"


def run_analysis(oof_path: Path, importance_path: Path, output_path: Path) -> dict:
    oof = pd.read_csv(oof_path)
    y_true = oof[TARGET_COLUMN].to_numpy()
    y_pred = oof["predicted_class"].to_numpy()

    results: dict = {}

    # 1. Confusion matrix + per-class report
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3, 4])
    results["confusion_matrix"] = cm.tolist()
    results["classification_report"] = classification_report(
        y_true, y_pred, labels=[0, 1, 2, 3, 4], output_dict=True, zero_division=0
    )
    results["overall"] = {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }

    # 2. Directional error: mean (predicted - true) per true class
    error = y_pred - y_true
    directional = (
        pd.DataFrame({"true_class": y_true, "error": error})
        .groupby("true_class")["error"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    results["directional_error_by_true_class"] = directional.to_dict(orient="records")
    print("Directional error (predicted - true) by true class:")
    print(directional.to_string(index=False))

    # 3. Cohort slices
    cohorts: dict[str, dict] = {}

    cohorts["by_type"] = {
        str(t): cohort_score(sub) for t, sub in oof.groupby("Type")
    }

    # Bin edges match the Phase 2 relationship EDA (crisp_dm_notes/02_data_understanding.md)
    # so cohort n's and rates are directly comparable to that earlier analysis.
    age_bins = [-1, 2, 6, 12, 60, 1000]
    age_labels = ["0-2mo", "3-6mo", "7-12mo", "13-60mo", "60mo+"]
    oof["age_bucket"] = pd.cut(oof["Age"], bins=age_bins, labels=age_labels)
    cohorts["by_age_bucket"] = {
        str(bucket): cohort_score(sub) for bucket, sub in oof.groupby("age_bucket", observed=True)
    }

    oof["has_photo"] = (oof["PhotoAmt"] > 0).map({True: "has_photo", False: "no_photo"})
    cohorts["by_has_photo"] = {
        str(k): cohort_score(sub) for k, sub in oof.groupby("has_photo")
    }

    oof["fee_group"] = (oof["Fee"] > 0).map({True: "fee_charged", False: "free"})
    cohorts["by_fee"] = {
        str(k): cohort_score(sub) for k, sub in oof.groupby("fee_group")
    }

    rescuer_counts = oof["RescuerID"].value_counts()
    oof["rescuer_listing_count"] = oof["RescuerID"].map(rescuer_counts)
    rescuer_bins = [0, 1, 5, 20, 1000]
    rescuer_labels = ["single_listing", "2-5_listings", "6-20_listings", "20+_listings"]
    oof["rescuer_bucket"] = pd.cut(oof["rescuer_listing_count"], bins=rescuer_bins, labels=rescuer_labels)
    cohorts["by_rescuer_listing_count"] = {
        str(k): cohort_score(sub) for k, sub in oof.groupby("rescuer_bucket", observed=True)
    }

    results["cohorts"] = cohorts
    print("\nCohort slices:")
    for cohort_name, buckets in cohorts.items():
        print(f"  {cohort_name}:")
        for bucket_name, stats in buckets.items():
            flag = " (SMALL N)" if stats["small_n_caution"] else ""
            print(f"    {bucket_name}: n={stats['n']} qwk={stats['qwk']:.3f} mae={stats['mae']:.3f} acc={stats['accuracy']:.3f}{flag}")

    # 4. Feature importance by family
    importances = pd.read_csv(importance_path)
    importances["family"] = importances["feature"].apply(feature_family)
    family_importance = (
        importances.groupby("family")["importance"].sum().sort_values(ascending=False)
    )
    family_importance_pct = (family_importance / family_importance.sum() * 100).round(2)
    results["feature_importance_by_family_pct"] = family_importance_pct.to_dict()
    print("\nFeature importance by family (% of total):")
    print(family_importance_pct.to_string())

    output_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSaved full error analysis to {output_path}")
    return results
