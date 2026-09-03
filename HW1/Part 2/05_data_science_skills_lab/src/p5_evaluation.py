"""CRISP-DM Phase 5 -- model-evaluation skill (the centrepiece of this phase).

1. Metric selection: PR-AUC/recall over accuracy (imbalanced churn, per
   [[imbalanced-data]]), StratifiedKFold(5) mean +/- std, both candidates.
2. ROC + PR curves, confusion matrices at multiple thresholds.
3. Calibration curve + Brier score, before/after CalibratedClassifierCV.
4. Lift/gains chart -- the retention team's actual decision tool.
5. Business evaluation: expected value of a retention campaign at each
   contact-capacity threshold, using clearly-labelled assumptions, resolving
   the hazard-based-vs-tenure-based LTV conflict explicitly.
6. Fits the FINAL end-to-end model (preprocessing + calibrated classifier)
   on the full train set and saves it as artifacts/model.joblib, plus
   artifacts/final_metrics.json for the Phase 6 hand-off contract.
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p4_repro import DEFAULT_SEED, assert_dataset_pinned, set_all_seeds  # noqa: E402
from p3_pipeline import build_preprocessor  # noqa: E402

from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

ARTIFACTS = ROOT / "artifacts"
FIG_DIR = ROOT / "reports" / "figures"


def load_data():
    train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
    test = pd.read_csv(ROOT / "data" / "processed" / "test.csv")
    X_train = train.drop(columns=["customerID", "Churn"])
    y_train = train["Churn"]
    X_test = test.drop(columns=["customerID", "Churn"])
    y_test = test["Churn"]
    return X_train, y_train, X_test, y_test, train, test


def build_candidates():
    xgb_results = json.loads((ARTIFACTS / "hyperparameter_tuning_results.json").read_text())
    xgb_best_params = xgb_results["xgboost"]["best_params"]

    logreg = Pipeline([
        ("prep", build_preprocessor()),
        ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED,
                                    class_weight="balanced")),
    ])
    xgboost = Pipeline([
        ("prep", build_preprocessor()),
        ("clf", XGBClassifier(**xgb_best_params, random_state=DEFAULT_SEED,
                               eval_metric="aucpr", n_jobs=1, verbosity=0)),
    ])
    return {"logreg_balanced": logreg, "xgboost_tuned": xgboost}


def section_1_cv_comparison(X_train, y_train, candidates, cv):
    print("== 1. Metric selection + CV comparison (mean +/- std, 5-fold) ==")
    results = {}
    for name, pipe in candidates.items():
        pr = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="average_precision")
        roc = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="roc_auc")
        rec = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="recall")
        acc = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="accuracy")
        results[name] = {
            "pr_auc_mean": pr.mean(), "pr_auc_std": pr.std(),
            "roc_auc_mean": roc.mean(), "roc_auc_std": roc.std(),
            "recall_mean": rec.mean(), "recall_std": rec.std(),
            "accuracy_mean": acc.mean(), "accuracy_std": acc.std(),
        }
        print(f"  {name:20s} PR-AUC={pr.mean():.4f}+/-{pr.std():.4f}  "
              f"ROC-AUC={roc.mean():.4f}+/-{roc.std():.4f}  recall={rec.mean():.4f}")
    return results


def section_2_curves_and_confusion(X_train, y_train, X_test, y_test, candidates):
    print("\n== 2. ROC/PR curves + confusion matrices at multiple thresholds ==")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fitted = {}
    probs = {}
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for name, pipe in candidates.items():
        pipe.fit(X_train, y_train)
        fitted[name] = pipe
        p = pipe.predict_proba(X_test)[:, 1]
        probs[name] = p
        fpr, tpr, _ = roc_curve(y_test, p)
        prec, rec, _ = precision_recall_curve(y_test, p)
        axes[0].plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y_test, p):.3f})")
        axes[1].plot(rec, prec, label=f"{name} (AP={average_precision_score(y_test, p):.3f})")
    axes[0].plot([0, 1], [0, 1], "k--", linewidth=1, label="chance")
    axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR"); axes[0].set_title("ROC curve (test)")
    axes[0].legend(fontsize=8)
    base_rate = y_test.mean()
    axes[1].axhline(base_rate, color="k", linestyle="--", linewidth=1,
                     label=f"no-skill ({base_rate:.3f})")
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
    axes[1].set_title("Precision-Recall curve (test)")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "p5_roc_pr_curves.png", dpi=130)
    plt.close(fig)
    print(f"  wrote {FIG_DIR / 'p5_roc_pr_curves.png'}")

    # Confusion matrices for the eventual final candidate (xgboost_tuned) at
    # multiple thresholds: default 0.5, and two business-motivated cuts.
    thresholds_to_show = [0.5, 0.3, 0.2]
    fig, axes = plt.subplots(1, len(thresholds_to_show), figsize=(4 * len(thresholds_to_show), 4))
    cm_results = {}
    for ax, thr in zip(axes, thresholds_to_show):
        pred = (probs["xgboost_tuned"] >= thr).astype(int)
        cm = confusion_matrix(y_test, pred)
        cm_results[str(thr)] = {
            "tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1]),
            "precision": float(precision_score(y_test, pred)),
            "recall": float(recall_score(y_test, pred)),
            "f1": float(f1_score(y_test, pred)),
        }
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(f"threshold={thr}\nP={cm_results[str(thr)]['precision']:.2f} "
                     f"R={cm_results[str(thr)]['recall']:.2f}")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                         color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["No churn", "Churn"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["No churn", "Churn"])
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    fig.suptitle("XGBoost (tuned) confusion matrix at multiple thresholds (test)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "p5_confusion_matrices.png", dpi=130)
    plt.close(fig)
    print(f"  wrote {FIG_DIR / 'p5_confusion_matrices.png'}")

    return fitted, probs, cm_results


def section_3_calibration(X_train, y_train, X_test, y_test, xgb_pipe):
    print("\n== 3. Calibration curve + Brier score, before/after CalibratedClassifierCV ==")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raw_pipe = xgb_pipe  # already fit on X_train in section 2
    raw_probs = raw_pipe.predict_proba(X_test)[:, 1]
    raw_brier = brier_score_loss(y_test, raw_probs)

    # Calibrate the WHOLE pipeline (preprocessing refits per internal fold too)
    calibrated = CalibratedClassifierCV(build_candidates()["xgboost_tuned"],
                                         method="sigmoid", cv=5)
    calibrated.fit(X_train, y_train)
    cal_probs = calibrated.predict_proba(X_test)[:, 1]
    cal_brier = brier_score_loss(y_test, cal_probs)

    frac_pos_raw, mean_pred_raw = calibration_curve(y_test, raw_probs, n_bins=10, strategy="quantile")
    frac_pos_cal, mean_pred_cal = calibration_curve(y_test, cal_probs, n_bins=10, strategy="quantile")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="perfectly calibrated")
    ax.plot(mean_pred_raw, frac_pos_raw, "o-", label=f"raw XGBoost (Brier={raw_brier:.4f})")
    ax.plot(mean_pred_cal, frac_pos_cal, "s-", label=f"calibrated (Brier={cal_brier:.4f})")
    ax.set_xlabel("Mean predicted probability (per bin)")
    ax.set_ylabel("Observed churn frequency (per bin)")
    ax.set_title("Calibration curve: raw vs CalibratedClassifierCV(sigmoid)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "p5_calibration.png", dpi=130)
    plt.close(fig)
    print(f"  raw Brier={raw_brier:.4f}  calibrated Brier={cal_brier:.4f}")
    print(f"  wrote {FIG_DIR / 'p5_calibration.png'}")

    return calibrated, {
        "raw_brier": float(raw_brier),
        "calibrated_brier": float(cal_brier),
        "improvement": float(raw_brier - cal_brier),
    }


def section_4_lift_gains(y_test, probs):
    print("\n== 4. Lift / gains chart ==")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = np.argsort(-probs)
    y_sorted = y_test.values[order]
    n = len(y_sorted)
    total_pos = y_sorted.sum()
    base_rate = total_pos / n

    deciles = np.arange(1, 11)
    cum_gains, lifts = [], []
    for d in deciles:
        k = int(np.ceil(n * d / 10))
        captured = y_sorted[:k].sum()
        cum_gains.append(captured / total_pos)
        lifts.append((captured / k) / base_rate)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(deciles * 10, [g * 100 for g in cum_gains], "o-", label="model")
    axes[0].plot([0, 100], [0, 100], "k--", label="random")
    axes[0].set_xlabel("% of customers contacted (ranked by risk)")
    axes[0].set_ylabel("% of churners captured (cumulative)")
    axes[0].set_title("Cumulative gains chart")
    axes[0].legend()

    axes[1].bar(deciles, lifts, color="#4c72b0")
    axes[1].axhline(1.0, color="k", linestyle="--", label="no-skill (lift=1)")
    axes[1].set_xlabel("Decile (1 = top 10% highest risk)")
    axes[1].set_ylabel("Lift")
    axes[1].set_title("Lift by decile")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "p5_lift_gains.png", dpi=130)
    plt.close(fig)
    print(f"  decile lifts: {[round(l, 2) for l in lifts]}")
    print(f"  wrote {FIG_DIR / 'p5_lift_gains.png'}")

    lift_at_10 = lifts[0]
    lift_at_20 = lifts[1]
    return {"decile_lifts": [float(l) for l in lifts],
            "decile_cumulative_gains": [float(g) for g in cum_gains],
            "lift_at_10pct": float(lift_at_10), "lift_at_20pct": float(lift_at_20)}


def section_5_business_ev(X_test, y_test, probs, business_metrics):
    print("\n== 5. Business evaluation: expected value of a retention campaign ==")
    n = len(y_test)
    total_churners = int(y_test.sum())
    base_rate = total_churners / n

    # ---- LTV ruling ----
    ltv_hazard = business_metrics["ltv"]["ltv_churn_rate_based"]           # 7899.96
    ltv_tenure = business_metrics["ltv"]["ltv_tenure_based_empirical"]      # 2283.30
    avg_tenure = business_metrics["ltv"]["avg_tenure_months"]               # 32.37
    mrr_m2m = business_metrics["revenue"]["arpu_by_contract"]["Month-to-month"]  # 66.40
    hazard_monthly = business_metrics["churn"]["monthly_churn_rate_hazard"]  # 0.008198

    implied_lifetime_months = 1 / hazard_monthly
    ltv_ruling = {
        "hazard_based_ltv": ltv_hazard,
        "hazard_based_implied_lifetime_months": round(implied_lifetime_months, 1),
        "tenure_based_ltv": ltv_tenure,
        "observed_mean_tenure_months": avg_tenure,
        "tenure_right_censored_at_months": 72,
        "ruling": (
            f"The hazard-based LTV (${ltv_hazard:,.2f}) is computed as ARPU / monthly hazard "
            f"= ${business_metrics['revenue']['arpu_all_customers']:.2f} / {hazard_monthly:.6f} "
            f"= ${ltv_hazard:,.2f}, which ALGEBRAICALLY implies an expected customer lifetime of "
            f"1/{hazard_monthly:.6f} = {implied_lifetime_months:.1f} months (~"
            f"{implied_lifetime_months/12:.1f} years). But tenure in this dataset is "
            f"right-censored at 72 months (~6 years) and the OBSERVED mean tenure is only "
            f"{avg_tenure:.1f} months -- no customer in the data has ever been observed to "
            f"reach 122 months. The hazard-based figure is a single-snapshot cross-sectional "
            f"hazard rate (aggregate customer-months churned / total customer-months observed), "
            f"and treating it as a constant, indefinitely-repeatable monthly risk for a customer "
            f"who has ALREADY survived to any given tenure is a survivorship-bias error: customers "
            f"who reach high tenure in a cross-section are disproportionately the ones for whom "
            f"month-to-month contracts have already converted to loyalty (churn hazard actually "
            f"DECREASES with tenure per the Phase 3 cohort/hazard analysis -- see "
            f"reports/figures/ts_hazard_by_tenure.png), so extrapolating the population-average "
            f"hazard forward forever massively overstates revenue that will never actually be "
            f"collected. VERDICT: hazard-based LTV ($7,899.96) is NOT used for campaign ROI. "
            f"The tenure-based empirical LTV (${ltv_tenure:,.2f}) is grounded in revenue actually "
            f"observed to have been collected (not extrapolated), so it is the safer anchor -- "
            f"though it itself is a lower bound (it mixes complete lifetimes from churned "
            f"customers with the still-ongoing, not-yet-fully-collected revenue of active "
            f"customers, so true LTV for an average customer is somewhat higher than $2,283.30, "
            f"just nowhere near $7,899.96)."
        ),
        "chosen_value_of_a_save_methodology": (
            "Rather than use either full-lifetime LTV figure directly in the EV arithmetic below "
            "(both have the biases explained above, and a full-lifetime payoff assumption is "
            "unusually optimistic for a monthly retention-campaign ROI decision), this evaluation "
            "uses a bounded, standard retention-economics framing: the value of a 'save' is the "
            "revenue protected over a stated decision horizon, not the customer's entire remaining "
            "lifetime. PRIMARY assumption: 12 months of Month-to-month ARPU "
            f"(${mrr_m2m:.2f}/mo x 12 = ${mrr_m2m*12:,.2f}) -- Month-to-month is used because "
            "these are the customers a churn model realistically targets (42.71% churn rate vs "
            "2.83% for Two-year, per Phase 1). This ${:.2f} figure is well below the "
            "tenure-based LTV anchor (${:,.2f}), so it is conservative relative to even the "
            "safer of the two LTV numbers. A sensitivity range using the tenure-based LTV as an "
            "upper alternative is also reported.".format(mrr_m2m * 12, ltv_tenure)
        ),
    }
    value_of_save_primary = mrr_m2m * 12
    value_of_save_upper = ltv_tenure

    print(f"  LTV ruling: hazard-based (${ltv_hazard:,.2f}, implies "
          f"{implied_lifetime_months:.0f}mo lifetime) REJECTED for campaign ROI -- "
          f"tenure-based (${ltv_tenure:,.2f}) used as conservative anchor; "
          f"primary value-of-save = 12mo M2M ARPU = ${value_of_save_primary:,.2f}")

    # ---- EV arithmetic across contact-capacity thresholds ----
    # ASSUMPTIONS (clearly labelled):
    offer_cost_per_contact = 50.0    # ASSUMPTION: cost of a retention offer/discount
    save_rate = 0.30                 # ASSUMPTION: fraction of contacted true-churners who are retained

    order = np.argsort(-probs)
    y_sorted = y_test.values[order]
    n = len(y_sorted)

    capacities = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 1.0]
    ev_table = []
    for cap in capacities:
        k = int(np.ceil(n * cap))
        contacted_true_churners = int(y_sorted[:k].sum())
        precision_at_k = contacted_true_churners / k
        expected_saves = contacted_true_churners * save_rate
        revenue_preserved_primary = expected_saves * value_of_save_primary
        revenue_preserved_upper = expected_saves * value_of_save_upper
        campaign_cost = k * offer_cost_per_contact
        net_ev_primary = revenue_preserved_primary - campaign_cost
        net_ev_upper = revenue_preserved_upper - campaign_cost
        ev_table.append({
            "capacity_pct": cap * 100,
            "n_contacted": k,
            "true_churners_contacted": contacted_true_churners,
            "precision_at_k": round(precision_at_k, 4),
            "expected_saves": round(expected_saves, 2),
            "campaign_cost": round(campaign_cost, 2),
            "revenue_preserved_primary_12mo_arpu": round(revenue_preserved_primary, 2),
            "net_ev_primary_12mo_arpu": round(net_ev_primary, 2),
            "revenue_preserved_upper_tenure_ltv": round(revenue_preserved_upper, 2),
            "net_ev_upper_tenure_ltv": round(net_ev_upper, 2),
            "roi_primary": round(revenue_preserved_primary / campaign_cost, 2) if campaign_cost else None,
        })

    best_by_primary_ev = max(ev_table, key=lambda r: r["net_ev_primary_12mo_arpu"])
    print("  EV table (primary = 12mo M2M ARPU value-of-save, $50/contact cost, 30% save rate):")
    for row in ev_table:
        print(f"    cap={row['capacity_pct']:>5.1f}%  n={row['n_contacted']:>4d}  "
              f"precision={row['precision_at_k']:.3f}  "
              f"net_EV=${row['net_ev_primary_12mo_arpu']:>10,.2f}  "
              f"ROI={row['roi_primary']}")
    print(f"  Best capacity by net EV (primary assumption): "
          f"{best_by_primary_ev['capacity_pct']:.0f}% "
          f"(n={best_by_primary_ev['n_contacted']}, net EV=${best_by_primary_ev['net_ev_primary_12mo_arpu']:,.2f})")

    return {
        "ltv_ruling": ltv_ruling,
        "assumptions": {
            "offer_cost_per_contact_usd": offer_cost_per_contact,
            "save_rate": save_rate,
            "value_of_save_primary_usd": round(value_of_save_primary, 2),
            "value_of_save_primary_methodology": "12 months of Month-to-month segment ARPU",
            "value_of_save_upper_usd": round(value_of_save_upper, 2),
            "value_of_save_upper_methodology": "tenure-based empirical LTV (conservative anchor, not hazard-based)",
        },
        "ev_table": ev_table,
        "recommended_capacity_pct": best_by_primary_ev["capacity_pct"],
        "recommended_capacity_net_ev_usd": best_by_primary_ev["net_ev_primary_12mo_arpu"],
    }


def section_6_fairness(fitted_model, X_test, y_test, test_df):
    print("\n== 6. Fairness / performance parity (gender, SeniorCitizen) ==")
    probs = fitted_model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)
    out = {}
    for col in ["gender", "SeniorCitizen"]:
        out[col] = {}
        for val in sorted(test_df[col].unique(), key=str):
            mask = (test_df[col] == val).values
            if mask.sum() < 10:
                continue
            yt, pt, pr = y_test.values[mask], preds[mask], probs[mask]
            out[col][str(val)] = {
                "n": int(mask.sum()),
                "base_rate": float(yt.mean()),
                "accuracy": float(accuracy_score(yt, pt)),
                "recall": float(recall_score(yt, pt)) if yt.sum() > 0 else None,
                "precision": float(precision_score(yt, pt, zero_division=0)),
                "pr_auc": float(average_precision_score(yt, pr)) if len(set(yt)) > 1 else None,
            }
        print(f"  {col}: {out[col]}")
    return out


def main():
    set_all_seeds(DEFAULT_SEED)
    assert_dataset_pinned()
    X_train, y_train, X_test, y_test, train_df, test_df = load_data()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=DEFAULT_SEED)
    candidates = build_candidates()

    cv_results = section_1_cv_comparison(X_train, y_train, candidates, cv)
    fitted, probs, cm_results = section_2_curves_and_confusion(
        X_train, y_train, X_test, y_test, candidates
    )
    calibrated_model, calib_results = section_3_calibration(
        X_train, y_train, X_test, y_test, fitted["xgboost_tuned"]
    )
    lift_results = section_4_lift_gains(y_test, probs["xgboost_tuned"])

    business_metrics = json.loads((ARTIFACTS / "business_metrics.json").read_text())
    ev_results = section_5_business_ev(X_test, y_test, probs["xgboost_tuned"], business_metrics)

    fairness_results = section_6_fairness(fitted["xgboost_tuned"], X_test, y_test, test_df)

    # ---- choose final threshold: precision>=0.30 floor, close to recommended capacity ----
    prec, rec, thr = precision_recall_curve(y_test, probs["xgboost_tuned"])
    target_capacity_pct = ev_results["recommended_capacity_pct"]
    n = len(y_test)
    k = int(np.ceil(n * target_capacity_pct / 100))
    order = np.argsort(-probs["xgboost_tuned"])
    chosen_threshold = float(probs["xgboost_tuned"][order[k - 1]])
    print(f"\nChosen decision threshold (at recommended {target_capacity_pct:.0f}% capacity): "
          f"{chosen_threshold:.4f}")

    # ---- FINAL model: calibrated XGBoost pipeline, refit on FULL train.csv ----
    final_candidate = build_candidates()["xgboost_tuned"]
    final_model = CalibratedClassifierCV(final_candidate, method="sigmoid", cv=5)
    final_model.fit(X_train, y_train)
    final_probs_test = final_model.predict_proba(X_test)[:, 1]
    final_pred_test = (final_probs_test >= chosen_threshold).astype(int)

    final_metrics = {
        "model": "CalibratedClassifierCV(sigmoid, cv=5) wrapping "
                 "Pipeline(build_preprocessor() -> Optuna-tuned XGBClassifier)",
        "roc_auc": float(roc_auc_score(y_test, final_probs_test)),
        "pr_auc": float(average_precision_score(y_test, final_probs_test)),
        "precision": float(precision_score(y_test, final_pred_test)),
        "recall": float(recall_score(y_test, final_pred_test)),
        "f1": float(f1_score(y_test, final_pred_test)),
        "accuracy": float(accuracy_score(y_test, final_pred_test)),
        "brier": float(brier_score_loss(y_test, final_probs_test)),
        "chosen_threshold": chosen_threshold,
        "chosen_threshold_capacity_pct": target_capacity_pct,
        "lift_at_10pct": lift_results["lift_at_10pct"],
        "lift_at_20pct": lift_results["lift_at_20pct"],
        "n_test": int(len(y_test)),
        "n_train": int(len(y_train)),
    }
    print("\n== FINAL model held-out TEST metrics ==")
    for k_, v_ in final_metrics.items():
        print(f"  {k_}: {v_}")

    joblib.dump(final_model, ARTIFACTS / "model.joblib")
    print(f"\nwrote {ARTIFACTS / 'model.joblib'}")

    (ARTIFACTS / "model_evaluation_cv_comparison.json").write_text(
        json.dumps({"cv_comparison": cv_results, "confusion_matrices_xgboost": cm_results,
                    "calibration": calib_results}, indent=2, default=float))
    (ARTIFACTS / "business_expected_value.json").write_text(
        json.dumps(ev_results, indent=2, default=float))
    (ARTIFACTS / "fairness_parity.json").write_text(
        json.dumps(fairness_results, indent=2, default=float))
    (ARTIFACTS / "final_metrics.json").write_text(json.dumps(final_metrics, indent=2, default=float))
    print("wrote model_evaluation_cv_comparison.json, business_expected_value.json, "
          "fairness_parity.json, final_metrics.json")


if __name__ == "__main__":
    main()
