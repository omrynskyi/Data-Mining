"""Chunk 21 — Phase 5 deep-dive: what did the model learn?

`final_model_feature_importance.csv` / `ordinal_model_feature_importance.csv`
(Chunks 16/19) already rank features by CatBoost's PredictionValuesChange —
useful for "how much does this feature matter overall," but it says nothing
about *direction* (does higher Age push predictions toward faster or slower
adoption?). This chunk adds SHAP values (Shapley additive explanations),
which decompose every individual prediction into a per-feature contribution,
so direction and typical magnitude can be reported per feature, not just an
aggregate importance score.

Model: the Chunk 18 final model (CatBoostRegressor, ordinal reformulation,
`depth=6, l2_leaf_reg=3, learning_rate=0.05`, ResNet18 `capped3_mean` image
embeddings — confirmed as the kept backbone in Chunk 20). A reference model
is fit on 100% of the labeled data (iterations = 329, the mean grouped
per-fold count from Chunk 19) for interpretability only, exactly as in
Chunks 16/19 — never used for scoring.

Categorical codes (Breed1/2, Color1/2/3, State) are decoded via the
official PetFinder data dictionaries in `petfinder-adoption-prediction/`
(breed_labels.csv, color_labels.csv, state_labels.csv). Binary/ordinal
codes (Gender, MaturitySize, FurLength, Vaccinated, Dewormed, Sterilized,
Health) are decoded using the standard PetFinder Kaggle competition
dictionary, cross-checked against this dataset's actually observed value
sets first (all matched the documented cardinalities exactly — no
unexpected codes).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "petfinder-adoption-prediction"
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "results" / "model_shap_analysis.json"

RANDOM_SEED = 2026
ALL_FEATURE_GROUPS = tuple(FEATURE_GROUPS)
IMAGE_EMBEDDING_BACKBONE = "resnet18"
IMAGE_EMBEDDING_VARIANT = "capped3_mean"
CATBOOST_CONFIG = {"depth": 6, "l2_leaf_reg": 3, "learning_rate": 0.05}
REFERENCE_ITERATIONS = 329  # mean of Chunk 18's grouped per-fold best_iterations

TOP_N_FEATURES = 20

# Standard PetFinder Kaggle competition dictionary, cross-checked against
# this dataset's observed value sets (Bash check: all matched exactly).
ORDINAL_CODE_LABELS = {
    "Type": {1: "Dog", 2: "Cat"},
    "Gender": {1: "Male", 2: "Female", 3: "Mixed (group)"},
    "MaturitySize": {1: "Small", 2: "Medium", 3: "Large", 4: "Extra Large"},
    "FurLength": {1: "Short", 2: "Medium", 3: "Long"},
    "Vaccinated": {1: "Yes", 2: "No", 3: "Not Sure"},
    "Dewormed": {1: "Yes", 2: "No", 3: "Not Sure"},
    "Sterilized": {1: "Yes", 2: "No", 3: "Not Sure"},
    "Health": {1: "Healthy", 2: "Minor Injury", 3: "Serious Injury"},
}


def load_label_maps():
    breed = pd.read_csv(DATA_ROOT / "breed_labels.csv")
    color = pd.read_csv(DATA_ROOT / "color_labels.csv")
    state = pd.read_csv(DATA_ROOT / "state_labels.csv")
    color_map = dict(zip(color["ColorID"], color["ColorName"]))
    state_map = dict(zip(state["StateID"], state["StateName"]))
    # Breed names depend on Type (dog breed IDs and cat breed IDs overlap numerically).
    breed_map = {(row.BreedID, row.Type): row.BreedName for row in breed.itertuples()}
    return breed_map, color_map, state_map


def decode_breed(breed_id: int, pet_type: int, breed_map: dict) -> str:
    if breed_id == 0:
        return "(unspecified/mixed)"
    return breed_map.get((breed_id, pet_type), f"unknown breed id {breed_id}")


def numeric_direction(values: np.ndarray, shap: np.ndarray) -> dict:
    corr = float(np.corrcoef(values, shap)[0, 1]) if np.std(values) > 0 else 0.0
    quartile_edges = np.quantile(values, [0, 0.25, 0.5, 0.75, 1.0])
    bins = np.digitize(values, quartile_edges[1:-1], right=True)
    quartile_means = [float(shap[bins == b].mean()) if (bins == b).any() else None for b in range(4)]
    return {"pearson_corr_value_vs_shap": corr, "mean_shap_by_quartile": quartile_means}


def categorical_direction(raw_values: pd.Series, shap: np.ndarray, decoder=None) -> list[dict]:
    df = pd.DataFrame({"value": raw_values.to_numpy(), "shap": shap})
    grouped = df.groupby("value")["shap"].agg(["mean", "count"]).reset_index()
    grouped = grouped.sort_values("mean", ascending=False)
    records = []
    for row in grouped.itertuples():
        label = decoder(row.value) if decoder else str(row.value)
        records.append({"value": row.value, "label": label, "mean_shap": float(row.mean), "count": int(row.count)})
    return records


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    breed_map, color_map, state_map = load_label_maps()

    print("=== Fitting reference model on 100% of labeled data (interpretability only) ===")
    builder = TreeFoldSafeFeatureBuilder(
        include_text=True,
        tabular_groups=ALL_FEATURE_GROUPS,
        image_embedding_variant=IMAGE_EMBEDDING_VARIANT,
        image_embedding_backbone=IMAGE_EMBEDDING_BACKBONE,
    )
    X_full = builder.fit_transform(frame)
    cat_cols = list(builder.categorical_feature_names)
    cat_idx = [X_full.columns.get_loc(c) for c in cat_cols]

    model = CatBoostRegressor(
        loss_function="RMSE",
        iterations=REFERENCE_ITERATIONS,
        depth=CATBOOST_CONFIG["depth"],
        learning_rate=CATBOOST_CONFIG["learning_rate"],
        l2_leaf_reg=CATBOOST_CONFIG["l2_leaf_reg"],
        random_seed=RANDOM_SEED,
        verbose=False,
        cat_features=cat_idx,
    )
    model.fit(X_full, y)

    print("=== Computing SHAP values ===")
    pool = Pool(X_full, cat_features=cat_idx)
    shap_full = model.get_feature_importance(pool, type="ShapValues")
    shap_values = shap_full[:, :-1]
    expected_value = float(shap_full[0, -1])
    print(f"expected_value (base prediction)={expected_value:.4f}")

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    pvc_importance = model.get_feature_importance()  # PredictionValuesChange, for cross-check

    ranking = pd.DataFrame(
        {
            "feature": X_full.columns,
            "mean_abs_shap": mean_abs_shap,
            "prediction_values_change": pvc_importance,
        }
    ).sort_values("mean_abs_shap", ascending=False)

    print("\nTop 20 features by mean |SHAP| (cross-checked against PredictionValuesChange rank):")
    print(ranking.head(20).to_string(index=False))

    results: dict = {"expected_value": expected_value, "top_features": []}

    top_features = ranking.head(TOP_N_FEATURES)["feature"].tolist()
    for feature in top_features:
        col_idx = X_full.columns.get_loc(feature)
        shap_col = shap_values[:, col_idx]
        entry = {
            "feature": feature,
            "mean_abs_shap": float(mean_abs_shap[col_idx]),
            "prediction_values_change": float(pvc_importance[col_idx]),
        }

        if feature in cat_cols:
            raw_col = frame[feature] if feature in frame.columns else X_full[feature]
            if feature == "Breed1":
                # Breed decoding needs each row's own Type (breed IDs overlap between dogs/cats).
                decoded = []
                tmp = pd.DataFrame({"Breed1": frame["Breed1"], "Type": frame["Type"], "shap": shap_col})
                g = tmp.groupby(["Breed1", "Type"])["shap"].agg(["mean", "count"]).reset_index()
                g = g.sort_values("mean", ascending=False)
                for row in g.itertuples():
                    decoded.append(
                        {
                            "value": f"Breed1={row.Breed1},Type={row.Type}",
                            "label": decode_breed(int(row.Breed1), int(row.Type), breed_map),
                            "mean_shap": float(row.mean),
                            "count": int(row.count),
                        }
                    )
                entry["by_category"] = decoded[:8] + decoded[-8:]
            elif feature in ("Color1", "Color2", "Color3"):
                decoder = lambda v: color_map.get(int(float(v)), f"unspecified ({v})") if float(v) != 0 else "(none)"
                entry["by_category"] = categorical_direction(raw_col, shap_col, decoder)
            elif feature == "State":
                decoder = lambda v: state_map.get(int(float(v)), f"unknown ({v})")
                entry["by_category"] = categorical_direction(raw_col, shap_col, decoder)
            elif feature in ORDINAL_CODE_LABELS:
                decoder = lambda v, f=feature: ORDINAL_CODE_LABELS[f].get(int(float(v)), f"unknown ({v})")
                entry["by_category"] = categorical_direction(raw_col, shap_col, decoder)
            else:
                entry["by_category"] = categorical_direction(raw_col, shap_col)
        elif feature in frame.columns:
            entry["direction"] = numeric_direction(frame[feature].to_numpy(dtype=float), shap_col)
        else:
            # Derived/abstract feature (text_svd_*, img_emb_pca_*) — no original-unit interpretation.
            entry["direction"] = numeric_direction(X_full[feature].to_numpy(dtype=float), shap_col)
            entry["note"] = "abstract PCA/SVD component; direction is w.r.t. the component's own scale, not an original raw feature"

        results["top_features"].append(entry)

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSaved full SHAP analysis to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
