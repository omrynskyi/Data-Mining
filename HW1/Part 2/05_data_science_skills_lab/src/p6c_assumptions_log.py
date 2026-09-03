"""
Phase 6 (communication/governance) — builds the real assumptions log for the Telco churn
lab using the analysis-assumptions-log skill's tracker functions.

NOTE ON A SHIPPED SKILL BUG: .claude/skills/analysis-assumptions-log/scripts/assumptions_tracker.py
defines both a `main()` (argparse CLI) and a bottom `if __name__ == "__main__": _demo()`.
The `__main__` guard calls `_demo()` unconditionally and never calls `main()`, so running the
script directly with --load/--report/--validate flags always silently falls through to the
hardcoded demo instead of honoring the CLI args. Per lab instructions, skill files under
.claude/skills/ are read-only, so this script imports the tracker's functions directly
instead of invoking the broken CLI. See analysis-retrospective.md for the full bug list.
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKER_PATH = REPO_ROOT / ".claude/skills/analysis-assumptions-log/scripts/assumptions_tracker.py"

spec = importlib.util.spec_from_file_location("assumptions_tracker", TRACKER_PATH)
tracker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tracker)


def build_log():
    log = tracker.new_log(
        analysis_name="Telco Customer Churn — full CRISP-DM lab (05_data_science_skills_lab)",
        analyst="Phase 6 communication & governance agent",
    )

    # --- Data assumptions ---
    tracker.add_assumption(
        log, "data",
        "The 11 customers with blank TotalCharges are new signups (tenure==0) who have not "
        "been billed yet, and can be safely imputed as $0 TotalCharges rather than dropped.",
        "Verified: 100% of the 11 null TotalCharges rows have tenure==0 (data_quality_scorecard.md "
        "consistency check); this matches the billing-cycle explanation exactly, not a random "
        "data-entry gap.",
        "high", "low",
    )
    tracker.add_assumption(
        log, "data",
        "The 'No internet service' / 'No phone service' sentinel values in the 6 add-on columns "
        "and MultipleLines are collapsed to a plain 'No' category during cleaning.",
        "Verified 100% redundant with InternetService=='No' / PhoneService=='No' (equal row "
        "counts); collapsing removes duplicate one-hot columns without losing information, since "
        "has_internet/has_phone flags carry that fact once (cleaning_report.md).",
        "high", "medium",
        "If a future feature needs to distinguish 'declined this add-on' from 'ineligible for "
        "this add-on', the collapse would need to be reversed — re-derivable from InternetService.",
    )
    tracker.add_assumption(
        log, "data",
        "tenure can stand in for a customer's true signup recency when no signup-date field exists, "
        "for cohort/time-series reconstruction.",
        "No signup_date column ships with this dataset; tenure is the only available recency proxy.",
        "medium", "high",
        "Already partially validated: quantified the resulting bias directly (below) rather than "
        "assuming it away.",
    )

    # --- Business logic assumptions ---
    tracker.add_assumption(
        log, "business_logic",
        "Cross-sectional cohort reconstruction (join_date = snapshot_date - tenure) systematically "
        "misplaces churned customers into more-recent cohort buckets than their true signup quarter, "
        "biasing older reconstructed cohorts' survival curves upward.",
        "Directly measured: oldest reconstructed cohort (2014Q1, n=434) sits +24.38pp above the "
        "pooled life-table baseline at matched tenure months — confirms the predicted direction "
        "and gives a quantified magnitude (cohort-analysis.md).",
        "high", "high",
        "Mitigation already applied: the pooled (non-cohort) hazard curve is used wherever a real "
        "decision depends on the number; individual cohort curves are presented for pattern-spotting "
        "only, with the bias called out inline.",
    )
    tracker.add_assumption(
        log, "business_logic",
        "The Contract-vs-churn comparison (month-to-month vs. two-year) is observational and cannot "
        "be interpreted as the causal effect of switching a customer's contract length.",
        "No randomization occurred; customers self-selected their contract. Confirmed by design: "
        "SRM check on the two groups is non-diagnostic here (no randomization to break), and the "
        "gap shrinks from +39.88pp unadjusted to +36.09pp after tenure-stratification but does not "
        "disappear, consistent with residual confounding (ab-test-analysis.md).",
        "high", "critical",
        "A real, powered randomized test is designed and specced (8pp MDE at 607/arm, or 5pp at "
        "1,552/arm) but not yet run. Do not size a retention-campaign ROI off the observational "
        "93% relative-lift number.",
    )
    tracker.add_assumption(
        log, "business_logic",
        "k=3 is used for the customer segmentation instead of the silhouette-optimal k=2.",
        "k=2 scores a higher silhouette (0.3369 vs. k=3's 0.3075), but produces a split too coarse "
        "to assign differentiated retention strategies to (2 groups vs. 3-7 the skill's own process "
        "recommends as actionable). k=3's 0.3075 still clears the skill's 0.3 validity bar "
        "(segmentation-analysis.md).",
        "high", "medium",
        "A judgement call, not an error — documented explicitly so a reviewer can re-derive k=2 "
        "results from the same elbow/silhouette table (segmentation_elbow_silhouette.png) if they "
        "weigh statistical fit over actionability differently.",
    )
    tracker.add_assumption(
        log, "business_logic",
        "Two conflicting customer lifetime value (LTV) figures exist — hazard-based ($7,899.96, "
        "implying ~122 months of expected lifetime) and tenure-based empirical ($2,283.30) — and "
        "the tenure-based figure is treated as the defensible one pending Phase 5's explicit ruling.",
        "The hazard-based estimate (ARPU / monthly hazard rate) is biased upward by single-snapshot "
        "survivorship: it implicitly assumes today's still-active customers' future hazard mirrors "
        "the population average forever, ignoring right-censoring at the observed 72-month tenure "
        "ceiling. business_metrics.json documents both formulas explicitly (ltv section).",
        "medium", "critical",
        "BLOCKING on Phase 5's written ruling in model-evaluation.md / final_metrics.json — "
        "impact-quantification.md states plainly which figure it uses and why, and flags if Phase 5 "
        "had not landed at time of writing.",
    )

    # --- Statistical assumptions ---
    tracker.add_assumption(
        log, "statistical",
        "Cramér's V and point-biserial correlations (feature-vs-churn association strength) are "
        "computed on the 5,634-row train split only, not the full 7,043-row population, to avoid "
        "leaking test-set information into feature/model decisions.",
        "Explicit instruction in the exploratory-data-analysis skill's Pitfalls section: fit only "
        "on train.",
        "high", "low",
        "Independently re-verified on the full population for this Phase 6 QA pass — full-data "
        "Cramér's V and z-test values differ slightly but not materially from the train-only "
        "figures (see analysis-qa-checklist.md discrepancy #1).",
    )
    tracker.add_assumption(
        log, "statistical",
        "The Kitagawa/Oaxaca-style two-term decomposition (mix effect + rate effect) fully "
        "attributes the Fiber-vs-non-Fiber churn gap without a separate interaction term.",
        "Standard simplification for a two-group, single-dimension decomposition; the two terms "
        "reconcile to the total gap up to the standard residual of this method "
        "(root-cause-investigation.md), which is small enough here not to change the "
        "78%/22% headline split materially.",
        "medium", "low",
    )

    # --- Technical assumptions ---
    tracker.add_assumption(
        log, "technical",
        "A fixed random seed (42) applied consistently across Python's random, NumPy, and "
        "(where used) PyTorch produces a reproducible train/test split and reproducible model runs "
        "across re-execution.",
        "Verified via repro_determinism_proof.json — same seed, same split, same downstream "
        "metrics across independent runs (reproducible-ml.md).",
        "high", "low",
    )

    return log


def main():
    log = build_log()
    out_json = REPO_ROOT / "artifacts" / "assumptions_log_telco.json"
    with open(out_json, "w") as f:
        json.dump(log, f, indent=2)

    report_text = tracker.report(log)
    out_report = REPO_ROOT / "artifacts" / "assumptions_log_report.txt"
    with open(out_report, "w") as f:
        f.write(report_text)

    print(report_text)
    critical = tracker.get_critical(log)
    print(f"\nCritical (unvalidated, low-confidence, high/critical-impact) count: {len(critical)}")
    return log


if __name__ == "__main__":
    main()
