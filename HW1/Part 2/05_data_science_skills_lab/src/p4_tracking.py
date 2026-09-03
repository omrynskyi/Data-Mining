"""CRISP-DM Phase 4 -- experiment-tracking skill.

Local, file-backed MLflow tracking (no server, no network):
tracking_uri = file:artifacts/mlruns, experiment "churn-classifier".

Logs every model variant produced across this phase as a REAL MLflow run
(params, metrics, tags, the fitted model artifact, and relevant figures),
then queries the tracking store with mlflow.search_runs to export a
run-comparison table, and demonstrates model-registry basics (register the
final calibrated model, transition it through stages) against the local
store.

Depends on artifacts already produced by: p4_imbalanced.py, p4_tuning.py,
p4_mlp_torch.py, p5_evaluation.py (run those first).
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p4_repro import DEFAULT_SEED, assert_dataset_pinned, set_all_seeds  # noqa: E402
from p3_pipeline import build_preprocessor  # noqa: E402

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

ARTIFACTS = ROOT / "artifacts"
FIG_DIR = ROOT / "reports" / "figures"
MLRUNS_DIR = ARTIFACTS / "mlruns"
DATA_HASH = json.loads((ROOT / "data" / "processed" / "dataset_meta.json").read_text())["raw_sha256"]

GIT_SHA_TAG = "no_git_repo (project not under version control -- see reproducible-ml doc)"


def load_data():
    train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
    test = pd.read_csv(ROOT / "data" / "processed" / "test.csv")
    X_train = train.drop(columns=["customerID", "Churn"])
    y_train = train["Churn"]
    X_test = test.drop(columns=["customerID", "Churn"])
    y_test = test["Churn"]
    return X_train, y_train, X_test, y_test


def common_tags(stage_note=""):
    return {
        "data_sha256": DATA_HASH,
        "seed": str(DEFAULT_SEED),
        "git_sha": GIT_SHA_TAG,
        "project": "telco-churn-crisp-dm",
        "phase": "04-modeling" if not stage_note else stage_note,
    }


def log_run(name, params, metrics, tags, model=None, model_flavor="sklearn",
            artifact_paths=None, step_metrics=None):
    with mlflow.start_run(run_name=name):
        mlflow.log_params(params)
        for k, v in tags.items():
            mlflow.set_tag(k, v)
        for k, v in metrics.items():
            if v is not None:
                mlflow.log_metric(k, float(v))
        if step_metrics:
            for metric_name, values in step_metrics.items():
                for step, val in enumerate(values):
                    mlflow.log_metric(metric_name, float(val), step=step)
        if model is not None and model_flavor == "sklearn":
            mlflow.sklearn.log_model(model, "model")
        for p in (artifact_paths or []):
            if Path(p).exists():
                mlflow.log_artifact(str(p))
        run_id = mlflow.active_run().info.run_id
        print(f"  logged run '{name}' -> run_id={run_id}")
        return run_id


def main():
    set_all_seeds(DEFAULT_SEED)
    assert_dataset_pinned()

    mlflow.set_tracking_uri(f"file:{MLRUNS_DIR}")
    experiment = mlflow.set_experiment("churn-classifier")
    print(f"MLflow tracking_uri={mlflow.get_tracking_uri()}  "
          f"experiment_id={experiment.experiment_id}")

    X_train, y_train, X_test, y_test = load_data()

    imbalanced = json.loads((ARTIFACTS / "imbalanced_data_comparison.json").read_text())
    tuning = json.loads((ARTIFACTS / "hyperparameter_tuning_results.json").read_text())
    mlp_cmp = json.loads((ARTIFACTS / "mlp_vs_sklearn_comparison.json").read_text())
    mlp_hist = json.loads((ARTIFACTS / "mlp_training_history.json").read_text())
    final_metrics = json.loads((ARTIFACTS / "final_metrics.json").read_text())

    run_ids = {}

    # ---- 1. baseline logreg ----
    print("\n1/7: baseline_logreg")
    baseline = Pipeline([("prep", build_preprocessor()),
                          ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED))])
    baseline.fit(X_train, y_train)
    run_ids["baseline_logreg"] = log_run(
        "baseline_logreg",
        params={"model": "LogisticRegression", "class_weight": "none", "seed": DEFAULT_SEED,
                "data_v": DATA_HASH[:12]},
        metrics={"cv_pr_auc_mean": imbalanced["a_baseline"]["pr_auc_mean"],
                 "cv_pr_auc_std": imbalanced["a_baseline"]["pr_auc_std"],
                 "cv_roc_auc_mean": imbalanced["a_baseline"]["roc_auc_mean"],
                 "cv_recall_mean": imbalanced["a_baseline"]["recall_mean"],
                 "cv_accuracy_mean": imbalanced["a_baseline"]["accuracy_mean"]},
        tags={**common_tags(), "imbalance_strategy": "none"},
        model=baseline,
        artifact_paths=[FIG_DIR / "p4_imbalanced_data_comparison.png"],
    )

    # ---- 2. class_weight balanced logreg ----
    print("2/7: logreg_class_weight_balanced")
    weighted = Pipeline([("prep", build_preprocessor()),
                          ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED,
                                                      class_weight="balanced"))])
    weighted.fit(X_train, y_train)
    run_ids["logreg_balanced"] = log_run(
        "logreg_class_weight_balanced",
        params={"model": "LogisticRegression", "class_weight": "balanced", "seed": DEFAULT_SEED,
                "data_v": DATA_HASH[:12]},
        metrics={"cv_pr_auc_mean": imbalanced["b_class_weight_balanced"]["pr_auc_mean"],
                 "cv_pr_auc_std": imbalanced["b_class_weight_balanced"]["pr_auc_std"],
                 "cv_roc_auc_mean": imbalanced["b_class_weight_balanced"]["roc_auc_mean"],
                 "cv_recall_mean": imbalanced["b_class_weight_balanced"]["recall_mean"]},
        tags={**common_tags(), "imbalance_strategy": "class_weight_balanced"},
        model=weighted,
    )

    # ---- 3. SMOTE-inside-CV honest logreg ----
    print("3/7: smote_honest_logreg (+ leakage comparison tag)")
    run_ids["smote_honest"] = log_run(
        "smote_honest_logreg",
        params={"model": "LogisticRegression+SMOTE(in-CV)", "seed": DEFAULT_SEED,
                "data_v": DATA_HASH[:12]},
        metrics={"cv_pr_auc_mean": imbalanced["c_smote_inside_cv_honest"]["pr_auc_mean"],
                 "cv_pr_auc_std": imbalanced["c_smote_inside_cv_honest"]["pr_auc_std"],
                 "cv_roc_auc_mean": imbalanced["c_smote_inside_cv_honest"]["roc_auc_mean"],
                 "leaky_pr_auc_mean_DO_NOT_TRUST": imbalanced["e_smote_before_split_LEAKY"]["pr_auc_mean"],
                 "leakage_inflation_pr_auc": imbalanced["_leakage_summary"]["leakage_inflation_pr_auc"]},
        tags={**common_tags(), "imbalance_strategy": "smote_in_cv",
              "leakage_check": "honest_vs_leaky_logged_side_by_side"},
        model=None,  # honest model object not persisted separately; the comparison is the point
    )

    # ---- 4. Optuna-tuned logreg ----
    print("4/7: logreg_optuna_tuned")
    lr_params = tuning["logreg"]["best_params"]
    tuned_lr = Pipeline([("prep", build_preprocessor()),
                          ("clf", LogisticRegression(max_iter=2000, random_state=DEFAULT_SEED,
                                                      class_weight="balanced", solver="liblinear",
                                                      **lr_params))])
    tuned_lr.fit(X_train, y_train)
    lr_test_probs = tuned_lr.predict_proba(X_test)[:, 1]
    run_ids["logreg_tuned"] = log_run(
        "logreg_optuna_tuned",
        params={"model": "LogisticRegression", "seed": DEFAULT_SEED, "data_v": DATA_HASH[:12],
                "optuna_n_trials": tuning["logreg"]["n_trials"], **lr_params},
        metrics={"cv_pr_auc_mean_optuna": tuning["logreg"]["best_value_pr_auc"],
                 "test_pr_auc": average_precision_score(y_test, lr_test_probs),
                 "test_roc_auc": roc_auc_score(y_test, lr_test_probs)},
        tags={**common_tags(), "tuning": "optuna_tpe"},
        model=tuned_lr,
        artifact_paths=[FIG_DIR / "p4_optuna_logreg_history.png",
                         FIG_DIR / "p4_optuna_logreg_importance.png"],
    )

    # ---- 5. Optuna-tuned XGBoost ----
    print("5/7: xgboost_optuna_tuned")
    xgb_params = tuning["xgboost"]["best_params"]
    tuned_xgb = Pipeline([("prep", build_preprocessor()),
                           ("clf", XGBClassifier(**xgb_params, random_state=DEFAULT_SEED,
                                                  eval_metric="aucpr", n_jobs=1, verbosity=0))])
    tuned_xgb.fit(X_train, y_train)
    xgb_test_probs = tuned_xgb.predict_proba(X_test)[:, 1]
    run_ids["xgboost_tuned"] = log_run(
        "xgboost_optuna_tuned",
        params={"model": "XGBClassifier", "seed": DEFAULT_SEED, "data_v": DATA_HASH[:12],
                "optuna_n_trials": tuning["xgboost"]["n_trials"],
                "optuna_n_pruned": tuning["xgboost"]["n_pruned"], **xgb_params},
        metrics={"cv_pr_auc_mean_optuna": tuning["xgboost"]["best_value_pr_auc"],
                 "test_pr_auc": average_precision_score(y_test, xgb_test_probs),
                 "test_roc_auc": roc_auc_score(y_test, xgb_test_probs)},
        tags={**common_tags(), "tuning": "optuna_tpe_median_pruner"},
        model=tuned_xgb,
        artifact_paths=[FIG_DIR / "p4_optuna_xgboost_history.png",
                         FIG_DIR / "p4_optuna_xgboost_importance.png"],
    )

    # ---- 6. MLP (torch) ----
    print("6/7: mlp_torch")
    run_ids["mlp"] = log_run(
        "mlp_torch",
        params={"model": "ChurnMLP(57-64-32-1)", "seed": DEFAULT_SEED, "data_v": DATA_HASH[:12],
                "optimizer": "AdamW", "lr": 1e-3, "weight_decay": 1e-2,
                "grad_clip_max_norm": 1.0, "early_stopping_patience": 10,
                "device": mlp_cmp["mlp"]["device"]},
        metrics={"best_val_loss": mlp_cmp["mlp"]["best_val_loss"],
                 "test_roc_auc": mlp_cmp["mlp"]["test_roc_auc"],
                 "test_pr_auc": mlp_cmp["mlp"]["test_pr_auc"],
                 "test_accuracy": mlp_cmp["mlp"]["test_accuracy_at_0.5"],
                 "test_recall": mlp_cmp["mlp"]["test_recall_at_0.5"],
                 "test_brier": mlp_cmp["mlp"]["test_brier"],
                 "n_epochs_trained": mlp_cmp["mlp"]["n_epochs_trained"]},
        tags={**common_tags(), "framework": "pytorch"},
        model=None,  # logged as a raw artifact below (torch flavor kept out of sklearn tracking loop)
        artifact_paths=[ARTIFACTS / "mlp_best.pt", FIG_DIR / "p4_mlp_training_curve.png"],
        step_metrics={"train_loss": mlp_hist["train_loss"], "val_loss": mlp_hist["val_loss"],
                      "val_pr_auc": mlp_hist["val_pr_auc"]},
    )

    # ---- 7. FINAL: calibrated XGBoost (loaded from the already-fit, verified model.joblib) ----
    print("7/7: final_calibrated_xgboost (candidate for registry)")
    final_model = joblib.load(ARTIFACTS / "model.joblib")
    with mlflow.start_run(run_name="final_calibrated_xgboost") as run:
        mlflow.log_params({"model": "CalibratedClassifierCV(sigmoid, cv=5)+XGBoost",
                            "seed": DEFAULT_SEED, "data_v": DATA_HASH[:12],
                            "chosen_threshold": final_metrics["chosen_threshold"],
                            **xgb_params})
        for k, v in {**common_tags(), "stage_candidate": "production", "final": "true"}.items():
            mlflow.set_tag(k, v)
        for k in ["roc_auc", "pr_auc", "precision", "recall", "f1", "accuracy", "brier",
                  "lift_at_10pct", "lift_at_20pct"]:
            mlflow.log_metric(k, float(final_metrics[k]))
        model_info = mlflow.sklearn.log_model(final_model, "model")
        for fig in ["p5_roc_pr_curves.png", "p5_confusion_matrices.png",
                    "p5_calibration.png", "p5_lift_gains.png"]:
            fig_path = FIG_DIR / fig
            if fig_path.exists():
                mlflow.log_artifact(str(fig_path))
        run_ids["final"] = run.info.run_id
        final_model_uri = model_info.model_uri
        print(f"  logged final run -> run_id={run.info.run_id}")

    # ---- Model registry basics against the local file store ----
    print("\n== Model registry ==")
    client = mlflow.tracking.MlflowClient()
    registered_name = "telco-churn-classifier"
    try:
        client.create_registered_model(registered_name)
        print(f"  created registered model '{registered_name}'")
    except mlflow.exceptions.MlflowException as e:
        print(f"  registered model already exists ({e.error_code}), continuing")

    mv = client.create_model_version(
        name=registered_name, source=final_model_uri, run_id=run_ids["final"]
    )
    print(f"  created model version {mv.version} for '{registered_name}'")

    client.transition_model_version_stage(
        name=registered_name, version=mv.version, stage="Staging",
        archive_existing_versions=False,
    )
    print(f"  transitioned version {mv.version} -> Staging")
    client.set_model_version_tag(registered_name, mv.version, "test_pr_auc",
                                  str(final_metrics["pr_auc"]))
    client.set_model_version_tag(registered_name, mv.version, "approved_by",
                                  "phase4-5-modeling-agent")

    staged = client.get_model_version(registered_name, mv.version)
    print(f"  verified: {registered_name} v{mv.version} stage={staged.current_stage}")

    # ---- Export run-comparison table via mlflow.search_runs ----
    print("\n== Exporting run comparison via mlflow.search_runs ==")
    runs_df = mlflow.search_runs(experiment_ids=[experiment.experiment_id],
                                  order_by=["start_time DESC"])
    keep_cols = [c for c in runs_df.columns if c.startswith(("tags.mlflow.runName", "metrics.",
                                                               "params.model", "params.seed"))]
    keep_cols = ["tags.mlflow.runName"] + [c for c in keep_cols if c != "tags.mlflow.runName"]
    comparison_df = runs_df[keep_cols].rename(columns={"tags.mlflow.runName": "run_name"})
    csv_path = ARTIFACTS / "mlflow_runs_comparison.csv"
    md_path = ARTIFACTS / "mlflow_runs_comparison.md"
    comparison_df.to_csv(csv_path, index=False)

    summary_cols = ["run_name", "metrics.cv_pr_auc_mean", "metrics.cv_pr_auc_mean_optuna",
                     "metrics.test_pr_auc", "metrics.pr_auc", "metrics.roc_auc",
                     "metrics.test_roc_auc"]
    summary_cols = [c for c in summary_cols if c in comparison_df.columns]
    with open(md_path, "w") as f:
        f.write("# MLflow run comparison (queried via mlflow.search_runs)\n\n")
        f.write(comparison_df[summary_cols].to_markdown(index=False))
        f.write("\n")
    print(f"  wrote {csv_path}")
    print(f"  wrote {md_path}")
    print(f"\n  {len(runs_df)} total runs in experiment '{experiment.name}'")


if __name__ == "__main__":
    main()
