"""CRISP-DM Phase 4 -- imbalanced-data skill.

Telco churn is 26.54% positive: moderate imbalance, NOT extreme (contrast
with fraud/disease at 1-5%). This script demonstrates, on the SAME
StratifiedKFold(5) folds so comparisons are apples-to-apples:

  (a) baseline LogisticRegression
  (b) class_weight="balanced"
  (c) SMOTE applied INSIDE the CV pipeline via imblearn.pipeline.Pipeline
  (d) threshold tuning on the baseline's out-of-fold probabilities
  (e) the resampling-leakage trap: SMOTE-before-split (inflated) vs
      SMOTE-inside-CV (honest)
  (f) the accuracy trap: a majority-class DummyClassifier's accuracy vs
      its recall / PR-AUC

Run: python3 src/p4_repro.py first is not required -- this script calls
set_all_seeds itself.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p4_repro import DEFAULT_SEED, assert_dataset_pinned, set_all_seeds  # noqa: E402
from p3_pipeline import build_preprocessor  # noqa: E402

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline as SkPipeline

from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

warnings.filterwarnings("ignore", category=FutureWarning)

ARTIFACTS = ROOT / "artifacts"


def load_train():
    train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
    X = train.drop(columns=["customerID", "Churn"])
    y = train["Churn"]
    return X, y


def main():
    set_all_seeds(DEFAULT_SEED)
    assert_dataset_pinned()
    X, y = load_train()
    pos_rate = y.mean()
    print(f"Train set: n={len(y)}, positive rate={pos_rate:.4f} "
          f"({'moderate' if 0.1 < pos_rate < 0.4 else 'extreme'} imbalance -- "
          "not extreme enough to reach for SMOTE reflexively)")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=DEFAULT_SEED)
    results = {}

    # ---- (a) baseline ----
    baseline = SkPipeline([
        ("prep", build_preprocessor()),
        ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED)),
    ])
    pr_auc = cross_val_score(baseline, X, y, cv=cv, scoring="average_precision")
    roc_auc = cross_val_score(baseline, X, y, cv=cv, scoring="roc_auc")
    acc = cross_val_score(baseline, X, y, cv=cv, scoring="accuracy")
    rec = cross_val_score(baseline, X, y, cv=cv, scoring="recall")
    results["a_baseline"] = {
        "pr_auc_mean": pr_auc.mean(), "pr_auc_std": pr_auc.std(),
        "roc_auc_mean": roc_auc.mean(), "roc_auc_std": roc_auc.std(),
        "accuracy_mean": acc.mean(), "accuracy_std": acc.std(),
        "recall_mean": rec.mean(), "recall_std": rec.std(),
    }
    print(f"(a) baseline           PR-AUC={pr_auc.mean():.4f}+/-{pr_auc.std():.4f}  "
          f"ROC-AUC={roc_auc.mean():.4f}  recall={rec.mean():.4f}  acc={acc.mean():.4f}")

    # ---- (b) class_weight="balanced" ----
    weighted = SkPipeline([
        ("prep", build_preprocessor()),
        ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED,
                                    class_weight="balanced")),
    ])
    pr_auc_w = cross_val_score(weighted, X, y, cv=cv, scoring="average_precision")
    roc_auc_w = cross_val_score(weighted, X, y, cv=cv, scoring="roc_auc")
    rec_w = cross_val_score(weighted, X, y, cv=cv, scoring="recall")
    acc_w = cross_val_score(weighted, X, y, cv=cv, scoring="accuracy")
    results["b_class_weight_balanced"] = {
        "pr_auc_mean": pr_auc_w.mean(), "pr_auc_std": pr_auc_w.std(),
        "roc_auc_mean": roc_auc_w.mean(), "roc_auc_std": roc_auc_w.std(),
        "accuracy_mean": acc_w.mean(), "accuracy_std": acc_w.std(),
        "recall_mean": rec_w.mean(), "recall_std": rec_w.std(),
    }
    print(f"(b) class_weight=bal.  PR-AUC={pr_auc_w.mean():.4f}+/-{pr_auc_w.std():.4f}  "
          f"ROC-AUC={roc_auc_w.mean():.4f}  recall={rec_w.mean():.4f}  acc={acc_w.mean():.4f}")

    # ---- (c) SMOTE INSIDE the CV pipeline (leak-free) ----
    # imblearn's Pipeline._validate_steps() rejects a nested sklearn Pipeline
    # as an intermediate step, so splice build_preprocessor()'s own steps
    # (engineer, prep) directly into the imblearn pipeline instead of nesting it.
    smote_honest = ImbPipeline(
        list(build_preprocessor().steps) + [
            ("smote", SMOTE(random_state=DEFAULT_SEED)),
            ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED)),
        ]
    )
    pr_auc_s = cross_val_score(smote_honest, X, y, cv=cv, scoring="average_precision")
    roc_auc_s = cross_val_score(smote_honest, X, y, cv=cv, scoring="roc_auc")
    rec_s = cross_val_score(smote_honest, X, y, cv=cv, scoring="recall")
    acc_s = cross_val_score(smote_honest, X, y, cv=cv, scoring="accuracy")
    results["c_smote_inside_cv_honest"] = {
        "pr_auc_mean": pr_auc_s.mean(), "pr_auc_std": pr_auc_s.std(),
        "roc_auc_mean": roc_auc_s.mean(), "roc_auc_std": roc_auc_s.std(),
        "accuracy_mean": acc_s.mean(), "accuracy_std": acc_s.std(),
        "recall_mean": rec_s.mean(), "recall_std": rec_s.std(),
    }
    print(f"(c) SMOTE-in-CV honest PR-AUC={pr_auc_s.mean():.4f}+/-{pr_auc_s.std():.4f}  "
          f"ROC-AUC={roc_auc_s.mean():.4f}  recall={rec_s.mean():.4f}  acc={acc_s.mean():.4f}")

    # ---- (e) the resampling-leakage trap: SMOTE BEFORE the split ----
    # Fit the (non-leaky, deterministic) preprocessor on the FULL train set,
    # transform everything, then oversample the FULL transformed set with
    # SMOTE -- synthetic minority points can now have their nearest neighbors
    # split across what CV will later call "train" and "validation" folds.
    # This is the exact leakage pattern the skill warns about, reproduced
    # deliberately so we can measure the inflation.
    prep_full = build_preprocessor()
    X_all_t = prep_full.fit_transform(X)
    X_res, y_res = SMOTE(random_state=DEFAULT_SEED).fit_resample(X_all_t, y)
    leaky_clf = LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED)
    pr_auc_leak = cross_val_score(leaky_clf, X_res, y_res, cv=cv, scoring="average_precision")
    roc_auc_leak = cross_val_score(leaky_clf, X_res, y_res, cv=cv, scoring="roc_auc")
    results["e_smote_before_split_LEAKY"] = {
        "pr_auc_mean": pr_auc_leak.mean(), "pr_auc_std": pr_auc_leak.std(),
        "roc_auc_mean": roc_auc_leak.mean(), "roc_auc_std": roc_auc_leak.std(),
        "note": "SMOTE fit on the FULL dataset before CV split -- synthetic "
                "neighbors leak across folds. Inflated relative to (c).",
    }
    print(f"(e) SMOTE-BEFORE-split PR-AUC={pr_auc_leak.mean():.4f}+/-{pr_auc_leak.std():.4f}  "
          f"ROC-AUC={roc_auc_leak.mean():.4f}   <-- LEAKY, compare to (c) honest")
    leakage_delta_pr_auc = pr_auc_leak.mean() - pr_auc_s.mean()
    leakage_delta_roc_auc = roc_auc_leak.mean() - roc_auc_s.mean()
    print(f"    leakage inflation: PR-AUC +{leakage_delta_pr_auc:.4f}, "
          f"ROC-AUC +{leakage_delta_roc_auc:.4f}")

    # ---- (d) threshold tuning on the baseline's out-of-fold probabilities ----
    oof_proba = cross_val_predict(baseline, X, y, cv=cv, method="predict_proba")[:, 1]
    prec, rec_arr, thr = precision_recall_curve(y, oof_proba)
    # business-agnostic demo target here (model-evaluation/business phase does
    # the capacity-constrained version): smallest threshold hitting >=50% precision
    ok = np.where(prec[:-1] >= 0.50)[0]
    chosen_thr = float(thr[ok[0]]) if len(ok) else 0.5
    pred_at_thr = (oof_proba >= chosen_thr).astype(int)
    pred_at_050 = (oof_proba >= 0.5).astype(int)
    results["d_threshold_tuning"] = {
        "default_threshold": 0.5,
        "default_precision": float(precision_recall_curve(y, oof_proba)[0][
            np.argmin(np.abs(thr - 0.5))]),
        "default_recall": float(recall_score(y, pred_at_050)),
        "tuned_threshold_for_precision_ge_0.50": chosen_thr,
        "tuned_recall_at_that_threshold": float(recall_score(y, pred_at_thr)),
        "tuned_accuracy_at_that_threshold": float(accuracy_score(y, pred_at_thr)),
    }
    print(f"(d) threshold tuning: default=0.5 recall={recall_score(y, pred_at_050):.4f} "
          f"-> tuned thr={chosen_thr:.4f} (precision>=0.50) "
          f"recall={recall_score(y, pred_at_thr):.4f}")

    # ---- (f) the accuracy trap: majority-class dummy predictor ----
    dummy = DummyClassifier(strategy="most_frequent", random_state=DEFAULT_SEED)
    dummy_acc = cross_val_score(dummy, X, y, cv=cv, scoring="accuracy")
    dummy_rec = cross_val_score(dummy, X, y, cv=cv, scoring="recall")
    dummy_prauc = cross_val_score(dummy, X, y, cv=cv, scoring="average_precision")
    results["f_accuracy_trap_dummy_majority"] = {
        "accuracy_mean": dummy_acc.mean(),
        "recall_mean": dummy_rec.mean(),
        "pr_auc_mean": dummy_prauc.mean(),
        "note": f"{dummy_acc.mean():.1%} accuracy predicting 'No churn' for "
                "everyone, catches ZERO churners (recall=0). Accuracy alone "
                "would make this look like a strong model.",
    }
    print(f"(f) accuracy trap: dummy majority-class acc={dummy_acc.mean():.4f} "
          f"but recall={dummy_rec.mean():.4f} PR-AUC={dummy_prauc.mean():.4f} "
          f"(vs baseline PR-AUC={pr_auc.mean():.4f})")

    results["_leakage_summary"] = {
        "smote_inside_cv_honest_pr_auc": pr_auc_s.mean(),
        "smote_before_split_leaky_pr_auc": pr_auc_leak.mean(),
        "leakage_inflation_pr_auc": leakage_delta_pr_auc,
        "smote_inside_cv_honest_roc_auc": roc_auc_s.mean(),
        "smote_before_split_leaky_roc_auc": roc_auc_leak.mean(),
        "leakage_inflation_roc_auc": leakage_delta_roc_auc,
    }
    results["_summary"] = {
        "positive_rate": float(pos_rate),
        "imbalance_verdict": "moderate (26.5%) -- class_weight/threshold tuning are "
                              "sufficient; SMOTE not clearly better here, consistent "
                              "with the skill's guidance not to over-apply it.",
        "best_by_pr_auc": max(
            [("baseline", pr_auc.mean()), ("class_weight_balanced", pr_auc_w.mean()),
             ("smote_honest", pr_auc_s.mean())],
            key=lambda t: t[1],
        )[0],
    }

    out_path = ARTIFACTS / "imbalanced_data_comparison.json"
    out_path.write_text(json.dumps(results, indent=2, default=float))
    print(f"\nwrote {out_path}")

    # ---- figure: PR curves + bar comparison ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    methods = ["baseline", "class_weight\nbalanced", "SMOTE\n(honest, in-CV)",
               "SMOTE\n(leaky, pre-split)", "dummy\n(majority)"]
    pr_vals = [pr_auc.mean(), pr_auc_w.mean(), pr_auc_s.mean(), pr_auc_leak.mean(),
               dummy_prauc.mean()]
    pr_errs = [pr_auc.std(), pr_auc_w.std(), pr_auc_s.std(), pr_auc_leak.std(), 0]
    colors = ["#4c72b0", "#4c72b0", "#4c72b0", "#c44e52", "#999999"]
    axes[0].bar(methods, pr_vals, yerr=pr_errs, capsize=4, color=colors)
    axes[0].set_ylabel("PR-AUC (average precision)")
    axes[0].set_title("PR-AUC across strategies (5-fold CV)\nred = leaky SMOTE-before-split")
    axes[0].axhline(pos_rate, color="black", linestyle="--", linewidth=1,
                     label=f"no-skill baseline ({pos_rate:.3f})")
    axes[0].legend(fontsize=8)
    axes[0].tick_params(axis="x", labelsize=8)

    axes[1].plot(rec_arr, prec, label="baseline (OOF predictions)")
    axes[1].axvline(recall_score(y, pred_at_thr), color="green", linestyle=":",
                     label=f"tuned thr={chosen_thr:.3f}")
    axes[1].axvline(recall_score(y, pred_at_050), color="orange", linestyle=":",
                     label="default thr=0.5")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title("Precision-Recall curve (out-of-fold, baseline)")
    axes[1].legend(fontsize=8)

    fig.tight_layout()
    fig_path = ROOT / "reports" / "figures" / "p4_imbalanced_data_comparison.png"
    fig.savefig(fig_path, dpi=130)
    plt.close(fig)
    print(f"wrote {fig_path}")


if __name__ == "__main__":
    main()
