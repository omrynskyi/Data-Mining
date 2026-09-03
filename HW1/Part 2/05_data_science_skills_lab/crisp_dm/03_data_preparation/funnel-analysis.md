---
skill: funnel-analysis
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - artifacts/funnel_analysis_report.md
  - artifacts/funnel_results.json
  - reports/figures/funnel_volume_churn.png
---

# funnel-analysis

## What the skill prescribes

Define ordered funnel steps → build the user-level funnel dataset → calculate step and overall
conversion + absolute drop-off (`funnel_analyzer.py`) → analyze time-to-convert → segment the
funnel by dimension → prioritize drop-offs by impact.

## Applied to Telco churn — service adoption funnel (no event log, so steps are nested service
tiers, not a session/conversion path)

`src/p3_funnel_analysis.py` reuses the skill's shipped `analyze_funnel()` directly, feeding it 5
nested/cumulative service-adoption steps: **Has phone → + Has internet → + ≥1 add-on → + ≥3
add-ons → + Support add-on (TechSupport)**, and adds churn-rate-per-stage (not in the shipped
script) plus a contract-type segment breakdown per the skill's step 5.

**Overall funnel** (n=5,634 train):

| Step | Users | Step conv | Overall conv | Churn rate |
|---|---|---|---|---|
| Has phone | 5,075 | 100.0% | 100.0% | 26.80% |
| + Has internet | 3,861 | 76.1% | 76.1% | 32.94% |
| + ≥1 add-on | 3,381 | 87.6% | 66.6% | 30.14% |
| + ≥3 add-ons | 1,993 | 59.0% | 39.3% | 21.88% |
| + Support add-on | 1,179 | 59.2% | 23.2% | **14.25%** |

Baseline churn (all customers): 26.54%. **Biggest drop-off**: ≥1→≥3 add-ons, −1,388 users (41.0%
of prior step). Churn rate rises through step 2 (adding internet — Fiber's elevated churn drags
this up, see `root-cause-investigation.md`) then falls steadily as customers accumulate add-ons
and support: the fully-loaded bundle (step 5) churns at little more than half the baseline rate.

**Segmented by contract** — Month-to-month has both the lowest overall conversion to the
fully-loaded bundle (10.9% vs 32.3% One-year, 43.6% Two-year) AND the highest churn rate at
every single stage (43.1%→30.5% across the funnel, vs 2.9%→3.8% for Two-year). Contract length,
not service depth alone, is the dominant lever — consistent with the root-cause and A/B-test
findings.

## Outputs produced

- `artifacts/funnel_analysis_report.md` — overall + 3 per-contract funnel tables.
- `artifacts/funnel_results.json` — machine-readable funnel + segment results.
- `reports/figures/funnel_volume_churn.png` — volume bars + churn-rate line by stage.
