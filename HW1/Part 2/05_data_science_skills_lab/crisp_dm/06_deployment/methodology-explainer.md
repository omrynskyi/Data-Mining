---
skill: methodology-explainer
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - crisp_dm/02_data_understanding/exploratory-data-analysis.md
  - crisp_dm/03_data_preparation/cohort-analysis.md
  - crisp_dm/03_data_preparation/segmentation-analysis.md
  - crisp_dm/03_data_preparation/root-cause-investigation.md
  - crisp_dm/03_data_preparation/ab-test-analysis.md
---

## What the skill prescribes

Six-step process: identify the audience tier (executive / business analyst / technical peer,
per `references/audience_depth_guide.md`); pick an explanation structure — narrative, layered,
or Q&A (`references/methodology_explanation_patterns.md`); draft the core explanation covering
question, data, method, assumptions, and key limitation; apply plain-language rewrites for
non-technical tiers; add an honest limitations paragraph (mandatory — "every methodology
explanation must include at least one honest limitation"); and produce the deliverable using
`assets/methodology_writeup_template.md`. This is distinct from
`technical-to-business-translator.md`: the translator recasts specific *results* in business
language; this document explains *how the analysis was done and why those methods were chosen*,
at three depths.

## Applied to Telco churn

Uses **Pattern 2 (Layered Writeup)** from `references/methodology_explanation_patterns.md` —
appropriate here because this lab's methodology has genuinely different content at each tier
(a cross-sectional reconstruction technique that only matters to a technical reviewer; a
segmentation choice that a business analyst needs to be able to challenge; a one-sentence
takeaway that is all an executive needs).

---

## Tier 1 — Executive summary (1 paragraph)

We analyzed 7,043 Telco customers' billing and service records — a single snapshot in time,
not a month-by-month history — to find out who is likely to leave and why. We measured which
customer and service attributes are most tied to churn, quantified how much revenue is at
stake, and grouped customers into segments to prioritize retention spend. The key limitation:
because we only have one snapshot per customer rather than a real event log, some
time-based patterns (like "what a 2014 signup cohort's true churn curve looked like") had to
be reconstructed indirectly and carry a known, documented bias — we flag every place that
bias matters and use the more reliable pooled estimate instead wherever a decision depends on it.

## Tier 2 — Business analyst / domain expert

**Data and scope:** `data/Telco-Customer-Churn.csv` — the Kaggle `blastchar/telco-customer-churn`
extract, 7,043 rows, 21 columns, one row per customer, as of a single point in time. No
timestamps, no transaction ledger, no separate parent/child tables. Population: all customers
in the extract; no filters applied at the whole-population level (Phase 2/3 feature work uses a
5,634-row train split for anything that must avoid leaking test-set information into feature
or model decisions, per `exploratory-data-analysis.md`).

**Method, in plain terms:**
1. **Business framing** — computed standard subscription metrics (MRR, ARPU, logo vs. revenue
   churn, ARR run-rate) directly from `MonthlyCharges` and the `Churn` flag.
2. **Association strength** — measured how strongly each customer attribute relates to churn
   using Cramér's V (categorical attributes) and point-biserial correlation (numeric
   attributes) — both are 0-to-1 (or -1-to-1) scores for "how tied together are these two
   things," computed only on the training data to avoid peeking at customers reserved for
   model evaluation.
3. **Root-cause decomposition** — for the standout Fiber-churn gap, split the total gap into
   "how much is because Fiber customers tend to be on different contract types" (mix effect)
   vs. "how much is because Fiber customers churn more even on the same contract type" (rate
   effect) — a standard technique (Kitagawa/Oaxaca-style decomposition) for separating
   composition changes from genuine rate changes.
4. **Cohort/time reconstruction** — since there is no real signup date, we back-calculated one
   from `tenure` (months since signup) to build cohort and survival curves. This only works
   cleanly for customers still active; for churned customers, `tenure` measures time-to-churn,
   not time-to-snapshot, which systematically misplaces churned customers into cohorts that
   look more recent than their true signup quarter (see Limitations).
5. **Segmentation** — grouped customers with k-means clustering on tenure, spend, and add-on
   count, testing k=2 through k=8 and picking the group count by a validity score (silhouette)
   balanced against how useful the groups are for targeting (see Assumptions).
6. **A/B power analysis** — since there was no actual experiment to analyze, we designed and
   sized a real future one: a contract-upgrade discount offered to month-to-month Fiber
   customers, using the standard two-proportion sample-size formula.

**Assumptions:**

| Assumption | Rationale |
|---|---|
| The 11 customers with blank `TotalCharges` are tenure=0 new signups, safe to impute as $0 billed | Verified: 100% of the 11 nulls have `tenure==0`; consistent with "no bill issued yet" |
| `tenure` can stand in for signup recency to reconstruct cohorts | No signup-date field exists; explicitly flagged as biased for churned customers (see Limitations) |
| k=3 segments, not the silhouette-optimal k=2 | k=2's higher silhouette (0.3369 vs. 0.3075) produces a group too coarse to assign differentiated retention strategies to — a deliberate actionability-over-fit-statistic trade-off, not an error |
| A random 42 seed reproducibly splits train/test the same way every re-run | Standard practice; verified via `repro_determinism_proof.json` |

**Limitations:**

- **The cohort/survival curves have a known, quantified upward bias for older reconstructed
  cohorts** (+24.38pp average survival inflation for the oldest cohort vs. the pooled
  life-table baseline) because churned customers get misassigned to more-recent cohort buckets
  by construction. We use the pooled (non-cohort) hazard curve, not individual cohort curves,
  wherever a real decision depends on the number.
- **The Contract-vs-churn comparison is observational, not experimental.** Customers chose
  their own contract length; the association (month-to-month churns 15x more than two-year)
  cannot be read as "switching a customer to a two-year contract causes a 93% relative churn
  reduction" without a real randomized test (which we designed and powered, but have not run).
- **This is a single snapshot**, so metrics that require a true monthly ledger (new/expansion/
  contraction MRR waterfall, true NRR) cannot be computed as normally defined for a recurring
  SaaS business; documented as an open data gap rather than approximated silently.

---

## Tier 3 — Technical appendix (peer reviewers)

**Cramér's V:** computed as `sqrt(chi2 / (n * (min(r,k) - 1)))` from a `scipy.stats.chi2_contingency`
crosstab of each categorical feature against `Churn`, on the 5,634-row train split. Point-biserial
r via `scipy.stats.pointbiserialr` for numeric features against the binary churn flag.

**Root-cause decomposition:** two-term Kitagawa/Oaxada-style split —
`mix_contribution = (share_fiber - share_nonfiber) * rate_nonfiber`,
`rate_contribution = share_fiber * (rate_fiber - rate_nonfiber)`, summed across Contract strata,
reconciling to the total rate gap up to the standard interaction residual of a two-term
decomposition. Verified independently on the full 7,043-row population outside the train split
(41.89% vs. 14.49%, z=25.85, p≈2.4e-147) — a different, larger-n figure than the train-only
root-cause report's 42.09% vs. 14.28% (z=23.47, p=8.66e-122); both are internally correct for
their respective populations, but the two documents should be read as train-split vs.
full-population estimates, not as a discrepancy (flagged and reconciled in
`analysis-qa-checklist.md`).

**Cohort reconstruction:** `join_date = snapshot_date(2020-03-01) - tenure_months`; cohort =
calendar quarter of `join_date`; life-table survival computed per cohort per elapsed month with
right-censoring for still-active customers. 25 cohorts, sizes 105-495, all above the skill's
n≥100 minimum.

**Segmentation:** `sklearn.cluster.KMeans`, features standardized (z-scored) tenure, ARPU
(MonthlyCharges), and add-on count; `k` swept 2-8; silhouette computed via
`sklearn.metrics.silhouette_score` on a sample; elbow via inertia. Final: k=3, silhouette=0.3075
(above the skill's 0.3 validity bar), seed=42.

**A/B power analysis:** two-proportion z-test sample-size formula
`n = 2*(z_{alpha/2} + z_beta)^2 * p*(1-p) / MDE^2`, alpha=0.05, power=0.80, baseline p=55.07%
(measured on the 1,707 current M2M+Fiber customers). Observational Contract-vs-churn comparison
run through the same skill's SRM/z-test machinery for mechanical demonstration only, then
explicitly invalidated as causal (see Tier 2 Limitations) and re-run as a tenure-stratified
covariate adjustment (+39.88pp unadjusted -> +36.09pp tenure-adjusted).

```python
# Cramer's V (from crisp_dm/02_data_understanding/exploratory-data-analysis.md methodology)
from scipy.stats import chi2_contingency
import numpy as np

def cramers_v(confusion_matrix):
    chi2 = chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    r, k = confusion_matrix.shape
    return np.sqrt(chi2 / (n * (min(r, k) - 1)))
```

## Outputs produced

- This layered methodology write-up (Tiers 1-3), per `assets/methodology_writeup_template.md`
- Cross-references the source phase docs rather than duplicating their full detail
