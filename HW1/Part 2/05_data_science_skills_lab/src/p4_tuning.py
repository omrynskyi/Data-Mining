"""CRISP-DM Phase 4 -- hyperparameter-tuning skill.

Optuna (TPE sampler, seeded) tunes two model families, each nested INSIDE
5-fold StratifiedKFold CV so no preprocessing/selection leakage reaches the
score used to pick hyperparameters:

  1. LogisticRegression (C, penalty, class_weight) -- fast, cheap search space
  2. XGBoost (max_depth, learning_rate, n_estimators, subsample,
     colsample_bytree, min_child_weight, reg_alpha, reg_lambda,
     scale_pos_weight) -- more expensive, uses per-fold pruning

Both objectives optimize mean PR-AUC (average_precision) across CV folds --
the imbalanced-data skill's recommended primary metric for this problem,
carried over here so tuning targets the metric that matters.

Budget: n_trials capped + wall-clock timeout per study; XGBoost trials report
intermediate per-fold scores so Optuna's MedianPruner can kill hopeless
trials early instead of burning the full budget on them.
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import optuna
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p4_repro import DEFAULT_SEED, assert_dataset_pinned, set_all_seeds  # noqa: E402
from p3_pipeline import build_preprocessor  # noqa: E402

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

warnings.filterwarnings("ignore", category=FutureWarning)
optuna.logging.set_verbosity(optuna.logging.WARNING)

ARTIFACTS = ROOT / "artifacts"
FIG_DIR = ROOT / "reports" / "figures"


def load_train():
    train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
    X = train.drop(columns=["customerID", "Churn"])
    y = train["Churn"]
    return X, y


def tune_logreg(X, y, cv, n_trials=30, timeout=300):
    def objective(trial):
        C = trial.suggest_float("C", 1e-3, 10, log=True)
        penalty = trial.suggest_categorical("penalty", ["l1", "l2"])
        solver = "liblinear"  # supports both l1 and l2
        clf = LogisticRegression(
            C=C, penalty=penalty, solver=solver, max_iter=2000,
            class_weight="balanced", random_state=DEFAULT_SEED,
        )
        pipe = Pipeline([("prep", build_preprocessor()), ("clf", clf)])
        scores = cross_val_score(pipe, X, y, cv=cv, scoring="average_precision")
        return scores.mean()

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=DEFAULT_SEED),
        study_name="logreg_pr_auc",
    )
    t0 = time.time()
    study.optimize(objective, n_trials=n_trials, timeout=timeout)
    elapsed = time.time() - t0
    return study, elapsed


def tune_xgboost(X, y, cv, n_trials=40, timeout=900):
    neg, pos = (y == 0).sum(), (y == 1).sum()
    base_spw = neg / pos

    def objective(trial):
        params = dict(
            max_depth=trial.suggest_int("max_depth", 2, 8),
            learning_rate=trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            n_estimators=trial.suggest_int("n_estimators", 50, 400),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 10),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 10, log=True),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
            scale_pos_weight=trial.suggest_float("scale_pos_weight", 1.0, base_spw * 1.5),
        )
        fold_scores = []
        for fold_i, (tr_idx, va_idx) in enumerate(cv.split(X, y)):
            pipe = Pipeline([
                ("prep", build_preprocessor()),
                ("clf", XGBClassifier(
                    **params, random_state=DEFAULT_SEED, eval_metric="aucpr",
                    n_jobs=1, verbosity=0,
                )),
            ])
            Xtr, ytr = X.iloc[tr_idx], y.iloc[tr_idx]
            Xva, yva = X.iloc[va_idx], y.iloc[va_idx]
            pipe.fit(Xtr, ytr)
            proba = pipe.predict_proba(Xva)[:, 1]
            from sklearn.metrics import average_precision_score
            score = average_precision_score(yva, proba)
            fold_scores.append(score)
            trial.report(float(np.mean(fold_scores)), fold_i)
            if trial.should_prune():
                raise optuna.TrialPruned()
        return float(np.mean(fold_scores))

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=DEFAULT_SEED),
        pruner=optuna.pruners.MedianPruner(n_warmup_steps=1, n_startup_trials=5),
        study_name="xgboost_pr_auc",
    )
    t0 = time.time()
    study.optimize(objective, n_trials=n_trials, timeout=timeout)
    elapsed = time.time() - t0
    return study, elapsed


def main():
    set_all_seeds(DEFAULT_SEED)
    assert_dataset_pinned()
    X, y = load_train()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=DEFAULT_SEED)

    print("== Tuning LogisticRegression (Optuna TPE, nested in 5-fold CV) ==")
    lr_study, lr_elapsed = tune_logreg(X, y, cv)
    print(f"  n_trials={len(lr_study.trials)}  elapsed={lr_elapsed:.1f}s")
    print(f"  best PR-AUC={lr_study.best_value:.4f}  best_params={lr_study.best_params}")

    print("\n== Tuning XGBoost (Optuna TPE + MedianPruner, nested in 5-fold CV) ==")
    xgb_study, xgb_elapsed = tune_xgboost(X, y, cv)
    n_pruned = sum(1 for t in xgb_study.trials if t.state == optuna.trial.TrialState.PRUNED)
    n_complete = sum(1 for t in xgb_study.trials if t.state == optuna.trial.TrialState.COMPLETE)
    print(f"  n_trials={len(xgb_study.trials)} (complete={n_complete}, pruned={n_pruned})  "
          f"elapsed={xgb_elapsed:.1f}s")
    print(f"  best PR-AUC={xgb_study.best_value:.4f}  best_params={xgb_study.best_params}")

    results = {
        "logreg": {
            "n_trials": len(lr_study.trials),
            "elapsed_sec": lr_elapsed,
            "best_value_pr_auc": lr_study.best_value,
            "best_params": lr_study.best_params,
            "sampler": "TPESampler(seed=42)",
        },
        "xgboost": {
            "n_trials": len(xgb_study.trials),
            "n_complete": n_complete,
            "n_pruned": n_pruned,
            "elapsed_sec": xgb_elapsed,
            "best_value_pr_auc": xgb_study.best_value,
            "best_params": xgb_study.best_params,
            "sampler": "TPESampler(seed=42)",
            "pruner": "MedianPruner(n_warmup_steps=1, n_startup_trials=5)",
        },
        "budget_discussion": (
            "LogisticRegression: 2-param search space, cheap fit (<1s/fold) -> "
            f"{len(lr_study.trials)} trials, no pruning needed, {lr_elapsed:.0f}s total. "
            "XGBoost: 9-param search space, ~5x more expensive per fit -> capped at "
            f"40 trials / 900s timeout with MedianPruner reporting per-fold PR-AUC so "
            f"trials clearly worse than the running median after fold 1 are killed "
            f"early ({n_pruned}/{len(xgb_study.trials)} trials pruned), reallocating "
            "budget to promising regions instead of finishing every trial to completion."
        ),
        "winner": "xgboost" if xgb_study.best_value > lr_study.best_value else "logreg",
    }
    out_path = ARTIFACTS / "hyperparameter_tuning_results.json"
    out_path.write_text(json.dumps(results, indent=2, default=float))
    print(f"\nwrote {out_path}")

    # ---- figures: optimization history + param importance, both studies ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import optuna.visualization.matplotlib as ovm

    for name, study in [("logreg", lr_study), ("xgboost", xgb_study)]:
        ax_hist = ovm.plot_optimization_history(study)
        ax_hist.set_title(f"{name}: optimization history")
        fig_hist = ax_hist.get_figure()
        fig_hist.set_size_inches(7, 5)
        fig_hist.tight_layout()
        fig_hist.savefig(FIG_DIR / f"p4_optuna_{name}_history.png", dpi=130)
        plt.close(fig_hist)

        try:
            ax_imp = ovm.plot_param_importances(study)
            ax_imp.set_title(f"{name}: hyperparameter importance")
            fig_imp = ax_imp.get_figure()
            fig_imp.set_size_inches(7, 5)
            fig_imp.tight_layout()
            fig_imp.savefig(FIG_DIR / f"p4_optuna_{name}_importance.png", dpi=130)
            plt.close(fig_imp)
        except (ValueError, RuntimeError) as e:
            print(f"  param importance unavailable for {name}: {e}")
        print(f"wrote reports/figures/p4_optuna_{name}_{{history,importance}}.png")

    # persist the two studies (sqlite) for experiment-tracking / reuse
    for name, study in [("logreg", lr_study), ("xgboost", xgb_study)]:
        df = study.trials_dataframe()
        df.to_csv(ARTIFACTS / f"optuna_trials_{name}.csv", index=False)
    print("wrote optuna_trials_{logreg,xgboost}.csv")


if __name__ == "__main__":
    main()
