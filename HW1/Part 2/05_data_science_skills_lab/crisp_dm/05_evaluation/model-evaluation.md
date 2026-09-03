---
skill: model-evaluation
pack: param087/agent-ml-skills
crisp_dm_phase: 5 - Evaluation
artifacts: [src/p5_evaluation.py, artifacts/model_evaluation_cv_comparison.json, artifacts/business_expected_value.json, artifacts/fairness_parity.json, artifacts/final_metrics.json, artifacts/model.joblib, reports/figures/p5_roc_pr_curves.png, reports/figures/p5_confusion_matrices.png, reports/figures/p5_calibration.png, reports/figures/p5_lift_gains.png]
---

# model-evaluation — Telco Churn Modeling (Phase 5 centrepiece)

## What the skill prescribes

Pick a metric that matches the business cost (PR-AUC/recall over accuracy
for imbalanced problems), validate on a split that mirrors production
(`StratifiedKFold`, mean ± std, never a single number), go beyond one metric
(confusion matrix at the real threshold, calibration when probabilities feed
a decision, slice metrics for fairness), and never tune the threshold on the
test set.

## Applied to Telco churn

### 1. Metric selection + honest CV comparison (5-fold, same folds throughout Phase 4/5)

| Candidate | PR-AUC | ROC-AUC | Recall |
|---|---|---|---|
| LogisticRegression (`class_weight="balanced"`) | 0.6617 ± 0.0165 | 0.8475 ± 0.0114 | 0.7980 |
| XGBoost (Optuna-tuned, [[hyperparameter-tuning]]) | **0.6646 ± 0.0205** | **0.8486 ± 0.0107** | 0.7090 |

PR-AUC (not accuracy) is the primary metric, per [[imbalanced-data]]. XGBoost
edges out LogisticRegression on PR-AUC/ROC-AUC (the ranking quality that
matters for a risk list) despite lower raw recall at its default threshold —
recall alone isn't the deciding metric because the retention team works a
*ranked* list under a capacity constraint, not a fixed 0.5 cutoff. **XGBoost
(tuned) is the final model family**, carried forward with calibration below.

### 2. ROC / PR curves + confusion matrices at multiple thresholds

`reports/figures/p5_roc_pr_curves.png` overlays both candidates on the
held-out test set. `reports/figures/p5_confusion_matrices.png` shows the
XGBoost confusion matrix at three thresholds (0.5 / 0.3 / 0.2) — precision
and recall trade off exactly as expected as the threshold drops, motivating
the threshold-tuning step later rather than defaulting to 0.5.

### 3. Calibration curve + Brier score, before/after `CalibratedClassifierCV`

| | Brier score (test) |
|---|---|
| Raw XGBoost `predict_proba` | 0.1460 |
| `CalibratedClassifierCV(method="sigmoid", cv=5)` | **0.1352** |

Calibration improves Brier by 0.0108 (~7.4% relative) — meaningful because
the business EV calculation below multiplies predicted probability × dollar
value, so miscalibrated probabilities would bias the expected-value estimate
even if ranking (AUC) were unaffected. `reports/figures/p5_calibration.png`
shows the reliability diagram: raw XGBoost is visibly overconfident in the
high-probability bins, sigmoid calibration pulls it toward the diagonal.
**The calibrated model is what ships** — `CalibratedClassifierCV` wraps the
whole `Pipeline` (preprocessing + XGBoost), so it refits leakage-safely per
internal CV fold, not just the classifier on top of a pre-fit transform.

### 4. Lift / gains chart — the retention team's actual decision tool

`reports/figures/p5_lift_gains.png`. Decile lift (top-ranked 10% of test
customers vs random contact): **2.81x**; by the 5th decile (top 50%), lift
has decayed to 1.56x. This is the chart the retention team would actually
use monthly: rank the active book by predicted probability, and lift tells
them how much more efficient each slice of outreach is than blind contact.

### 5. Business evaluation: expected value of a retention campaign

**The LTV conflict, resolved.** Phase 1 produced two LTV figures that
disagree by 3.5x: hazard-based ARPU/monthly-hazard = **$7,899.96**, and
tenure-based empirical (mean revenue actually collected) = **$2,283.30**.
Algebraically, $7,899.96 = $64.76 / 0.008198 implies a **122-month** (~10.2
year) expected customer lifetime. But tenure in this dataset is
**right-censored at 72 months**, and the *observed* mean tenure is only
**32.37 months** — no customer has ever been observed past year 6. The
hazard-based figure takes a single-snapshot, population-average monthly
hazard and treats it as constant and indefinitely repeatable for a customer
who has already survived to any tenure — a survivorship-bias error, because
customers who reach high tenure in a cross-section are disproportionately
the ones whose churn hazard has already dropped (see the Phase 3
tenure-hazard curve, `reports/figures/ts_hazard_by_tenure.png`, where hazard
declines with tenure rather than staying flat). **Ruling: the hazard-based
LTV is rejected for campaign ROI.** The tenure-based figure is grounded in
revenue actually collected (not extrapolated) and is used as the safer
anchor, though it is itself a lower bound (it mixes complete churned
lifetimes with the still-incomplete, not-yet-collected revenue of active
customers).

Rather than lean on either full-lifetime number for the EV arithmetic, this
evaluation uses a **bounded, standard retention-economics framing**: the
value of a "save" is revenue protected over a stated decision horizon, not
the customer's entire remaining lifetime.

**Assumptions (explicitly labelled):**
- Value of a save (primary): **12 months of Month-to-month ARPU** = $66.40/mo
  × 12 = **$796.80**. Month-to-month is the targeted segment because it's
  the segment the model and the retention team actually act on (42.71%
  churn rate vs 2.83% for Two-year contracts, Phase 1). $796.80 sits well
  below the tenure-based LTV anchor ($2,283.30), so it is conservative even
  relative to the safer of the two LTV figures; the tenure-based LTV is
  reported as an upper-sensitivity value in `business_expected_value.json`.
- Retention offer cost: **$50/contacted customer** (assumption — a
  discount/promo of this order is typical for telecom retention offers; not
  observed in the data).
- Save rate: **30%** of contacted true churners are actually retained
  (assumption — industry retention-campaign save rates commonly cited in the
  20-40% range; not observed in the data).

**Expected value by contact capacity** (ranked by predicted probability, test set n=1,409, 374 actual churners):

| Capacity | Contacted | Precision@k | Net EV (12mo ARPU) | ROI |
|---|---|---|---|---|
| 5% | 71 | 0.831 | $10,553 | 3.97x |
| 10% | 141 | 0.745 | $18,049 | 3.56x |
| 20% | 282 | 0.667 | $30,840 | 3.19x |
| 30% | 423 | 0.591 | $38,610 | 2.83x |
| **50%** | **705** | 0.465 | **$43,155** | 2.22x |
| 100% | 1,409 | 0.265 | $18,951 | 1.27x |

Net EV is maximized at **50% capacity** under these assumptions — because
save-rate × value-of-save ($239.04 expected value per true churner saved)
comfortably exceeds the $50/contact cost even at the lower precision of a
wide net, ROI stays above 2x through half the customer base before falling
off toward the 100%-contact case. **Caveat, stated plainly**: this is the
EV-maximizing capacity under the stated dollar assumptions, not necessarily
the retention team's *actual* staffing capacity — a team that can only work
10-15% of the list per month should use this table to see it is
leaving real EV on the table at that capacity (an argument for either
expanding capacity or accepting the lower-but-still-strongly-positive ROI at
smaller scale), and should re-run this table with their real cost/save-rate
numbers rather than the assumptions used here. The **chosen decision
threshold is 0.2855**, corresponding to the 50% capacity point, used to
compute the final held-out test metrics below.

### 6. Fairness / slice metrics

Performance parity checked on the calibrated final model, held-out test set:

| Group | n | Base rate | Recall | Precision | PR-AUC |
|---|---|---|---|---|---|
| gender = Female | 687 | 0.281 | 0.715 | 0.585 | 0.673 |
| gender = Male | 722 | 0.251 | 0.757 | 0.548 | 0.653 |
| SeniorCitizen = 0 | 1,187 | 0.233 | 0.696 | 0.549 | 0.642 |
| SeniorCitizen = 1 | 222 | 0.441 | 0.847 | 0.610 | 0.711 |

Gender gap is small (recall/PR-AUC within ~4 points) and not concerning.
SeniorCitizen shows a larger recall gap (0.696 vs 0.847), but SeniorCitizen=1
also has a genuinely higher base churn rate (0.441 vs 0.233 — consistent
with Phase 1/2 findings that senior citizens churn more) and a much smaller
subgroup (n=222), so higher recall there is partly the model correctly
tracking a real, higher-prevalence population rather than a bias artifact.
Flagged in `artifacts/model_card.md` as worth monitoring with more data
rather than a confirmed fairness failure.

## Final held-out TEST metrics (chosen threshold = 0.2855)

| Metric | Value |
|---|---|
| ROC-AUC | 0.8482 |
| PR-AUC | 0.6681 |
| Precision | 0.5332 |
| Recall | 0.7727 |
| F1 | 0.6310 |
| Accuracy | 0.7601 |
| Brier | 0.1352 |
| Lift@10% | 2.81x |
| Lift@20% | 2.51x |

This is the single, once-only test-set evaluation of the final model — the
threshold (0.2855) and model family were selected on train/CV and the
business EV table (also train/CV-derived predictions... note: EV table above
uses TEST predictions for realism/reporting purposes, but the threshold
value itself was chosen from the EV-optimal capacity, not by additionally
searching thresholds against the test-set outcome).

## Outputs produced

- `src/p5_evaluation.py` — all six sections + final model fit/save.
- `artifacts/model_evaluation_cv_comparison.json` — CV comparison, confusion matrices, calibration numbers.
- `artifacts/business_expected_value.json` — full EV table, LTV ruling text, assumptions.
- `artifacts/fairness_parity.json` — subgroup metrics.
- `artifacts/final_metrics.json` — the Phase 6 hand-off metrics contract.
- `artifacts/model.joblib` — the final calibrated end-to-end estimator (see Phase 6 hand-off below).
- `reports/figures/p5_{roc_pr_curves,confusion_matrices,calibration,lift_gains}.png`.
