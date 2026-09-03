---
skill: dashboard-specification
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - crisp_dm/06_deployment/dashboard-specification.md
---

# Dashboard Specification — Telco Retention Risk Dashboard

## What the skill prescribes

`.claude/skills/dashboard-specification/SKILL.md` prescribes six steps: state
the purpose as one sentence ("this dashboard answers [question] for
[audience] who need to [decision]"); profile each distinct audience
separately rather than one dashboard with more filters; define a metric
hierarchy capped at 10-12 metrics (hero KPIs → context → diagnostic detail,
per `references/dashboard_design_principles.md`'s "single question test" and
information-hierarchy levels); design layout with the hero → trends →
breakdowns → details pattern, F-pattern top-left priority; specify
interactivity and justify every filter/drill-down; document data sources,
refresh cadence and success criteria per
`references/dashboard_requirements_guide.md`'s requirements-capture template
and sign-off checklist. `assets/dashboard_spec_template.md` is the filled
deliverable format used below.

## Applied to Telco churn

The stakeholder, decision, and success criteria below are carried over
verbatim from the already-completed intake interview in
`crisp_dm/01_business_understanding/stakeholder-requirements-gathering.md`
(VP of Customer Retention; root question: *which active customers have the
highest churn probability and, among those, the most revenue at risk*). This
spec turns that into a buildable dashboard brief. Every metric definition
below is traced to its `metrics:` entry in `artifacts/semantic_model_telco.yml`
so a BI developer does not have to guess a calculation.

---

# Dashboard Specification

**Dashboard name:** Telco Retention Risk Dashboard
**Owner:** Analytics team (this project) — day-to-day accuracy owner; VP of
Customer Retention is the business owner and sign-off authority
**Date:** 2026-09-02
**Status:** Draft — pending stakeholder sign-off per
`dashboard_requirements_guide.md`'s sign-off checklist (see bottom)

---

## Purpose

**Primary question this dashboard answers:**
> Which active customers should the retention team call this month, and how
> much recurring revenue is at risk across the base right now?

This passes the skill's single-question test: it is one sentence, and every
tile on Page 1 exists to answer it. (Page 2 answers a second, narrower
question — see below — kept on a separate page rather than crowding Page 1,
per the "users with different needs need different dashboards, not more
filters" principle.)

**Primary audience:** Retention team leads. Daily/weekly users, medium
technical comfort (comfortable with a sortable table and filters, not SQL).
Primary task: work the ranked call list top-down.

**Secondary audience:** VP of Customer Retention. Monthly user, needs the
aggregate/exec view (Page 2) to report revenue-at-risk trend up to the COO —
does not need or want the row-level call list.

**Usage frequency:** Retention leads — daily during active outreach weeks,
otherwise weekly. VP — monthly (tied to the monthly reporting cycle
established in the intake interview).

**Access method:** Desktop browser (retention leads work the list at their
desk); Page 2 (exec summary) must also render acceptably on mobile since the
VP may check it before a COO meeting.

---

## Metrics

All rows trace to `artifacts/semantic_model_telco.yml`. Metrics not yet
defined there (model score, risk band) are marked accordingly and sourced
from the Phase 4/5 model artifact contract instead.

| Metric | Definition | Source | Owner | Refresh | Acceptable lag |
|---|---|---|---|---|---|
| MRR at risk | Sum of `monthly_charges_sum` measure, filtered to active customers with churn-risk score ≥ the chosen alert threshold (see Alerts). Base MRR metric = `mrr` in `semantic_model_telco.yml:124` | `stg_telco_customers` + model scores | Analytics | Monthly | 24h |
| Logo churn rate (realized, trailing) | `churn_rate` metric, `semantic_model_telco.yml:174` — churned customers / total customers | `stg_telco_customers` | Analytics | Monthly | 24h |
| Revenue churn rate | `revenue_churn_rate` metric, `semantic_model_telco.yml:204` — churned customers' MonthlyCharges / total MRR | `stg_telco_customers` | Analytics | Monthly | 24h |
| ARPU | `arpu` metric, `semantic_model_telco.yml:150` — `monthly_charges_sum` / `customer_count` | `stg_telco_customers` | Analytics | Monthly | 24h |
| Churn-risk score (0-1) | Calibrated `predict_proba` output of the Phase 4/5 model artifact (`artifacts/model.joblib` / `artifacts/inference_contract.json`) — **not yet in the semantic model**; documented gap, see Anti-requirements | `artifacts/model.joblib` batch-scored monthly | Data Science | Monthly (batch) | 24h after batch score run |
| Risk band (High/Medium/Low) | Threshold bucketing of churn-risk score per `artifacts/inference_contract.json`'s decision threshold — same gap as above | Model output | Data Science | Monthly | 24h |
| Top risk driver(s) | Per-customer SHAP-style top 2-3 features from the model artifact, mapped to plain-language labels (e.g. "month-to-month contract", "fiber, no tech support") | Model output | Data Science | Monthly | 24h |
| Churn rate by contract | `churn_rate` metric sliced by the `contract` dimension, `semantic_model_telco.yml:30-39` | `stg_telco_customers` | Analytics | Monthly | 24h |
| Churn rate by internet service | `churn_rate` sliced by `internet_service` dimension, `semantic_model_telco.yml:41-47` | `stg_telco_customers` | Analytics | Monthly | 24h |
| Segment (k-means cluster) | `artifacts/segment_profile_kmeans.csv` cluster assignment + label — **not yet in the semantic model as a dimension**; documented gap | `artifacts/segments.csv` | Data Science | Monthly (re-run with batch score) | 24h |
| Tenure bucket | `tenure_bucket` dimension, `semantic_model_telco.yml:61-77` | `stg_telco_customers` | Analytics | Monthly | 24h |

**Metric count check:** 11 distinct metrics across both pages — at the
skill's stated ceiling of 10-12; no further metrics should be added without
retiring one (per `dashboard_design_principles.md`'s "trying to do too much"
warning).

---

## Layout specification

### Page 1: Retention Call List (primary audience: retention leads)

**Primary question:** Who do I call this week, in what order?

```
┌─────────────────────────────────────────────────────────────────────┐
│  HERO ROW (KPI cards, no interaction needed)                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────┐│
│  │ MRR AT RISK   │ │ HIGH-RISK     │ │ LOGO CHURN    │ │ REVENUE  ││
│  │ (High band)   │ │ CUSTOMER CT   │ │ (trailing)    │ │ CHURN    ││
│  │ $XX,XXX/mo    │ │ N,NNN         │ │ 26.5%         │ │ 30.5%    ││
│  └───────────────┘ └───────────────┘ └───────────────┘ └──────────┘│
├─────────────────────────────────────────────────────────────────────┤
│  RANKED CALL LIST (main content — table, sortable, top-left         │
│  priority per F-pattern)                                            │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ CustomerID │ RiskScore │ Band │ MRR │ Top drivers │ Tenure    │ │
│  │  sortable, default sort = RiskScore x MRR (expected value) desc│ │
│  └───────────────────────────────────────────────────────────────┘ │
├───────────────────────────────┬───────────────────────────────────┤
│  BOTTOM-LEFT                  │  BOTTOM-RIGHT                      │
│  Bar: risk-band count by      │  Bar: MRR at risk by segment       │
│  contract type                │  (3 k-means segments)              │
└───────────────────────────────┴───────────────────────────────────┘
```

| Position | Chart type | Metric | Dimensions | Filters applied |
|---|---|---|---|---|
| Hero 1 (top-left) | KPI card | MRR at risk | — | High-risk band, active only |
| Hero 2 | KPI card | High-risk customer count | — | Active only |
| Hero 3 | KPI card | Logo churn rate (trailing) | — | Sticky filters |
| Hero 4 | KPI card | Revenue churn rate (trailing) | — | Sticky filters |
| Main (center, full-width) | Sortable table | RiskScore, Band, MRR, top drivers, tenure | Row = customer | All sticky filters; row-click drills to Customer Detail (see Interactivity) |
| Bottom-left | Vertical bar | Count of customers | By contract × risk band (stacked) | Sticky filters |
| Bottom-right | Vertical bar | MRR at risk | By segment (3 k-means clusters) | Sticky filters |

**Default time range:** N/A — this is a snapshot dataset (documented gap:
no dated ledger; see `semantic_model_telco.yml:84-97`), so "time range" is
replaced by **scoring batch date** (the date the model last ran), shown as a
"Data as of [date]" stamp instead of a date-range picker. This is a
deliberate deviation from the template's default time-range field, made
explicit here so a builder doesn't hunt for a date filter that shouldn't
exist.

**Sticky filters (apply to all Page 1 charts):** risk band, contract type,
internet service type, segment.

---

### Page 2: Executive Retention Summary (secondary audience: VP)

**Primary question:** How much revenue is at risk, and is it improving?

```
┌─────────────────────────────────────────────────────────────────────┐
│  HERO ROW                                                            │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │
│  │ MRR AT RISK   │ │ ARPU          │ │ REVENUE CHURN │              │
│  │ (total)       │ │               │ │ RATE          │              │
│  └───────────────┘ └───────────────┘ └───────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│  CENTER: Churn rate by contract (bar) | Churn rate by internet (bar)│
├─────────────────────────────────────────────────────────────────────┤
│  BOTTOM: Segment value x risk bubble (reused from                   │
│  reports/figures/p6_segment_value_risk_bubble.png logic)            │
└─────────────────────────────────────────────────────────────────────┘
```

| Position | Chart type | Metric | Dimensions | Filters |
|---|---|---|---|---|
| Hero 1 | KPI card | MRR at risk (total, all bands) | — | — |
| Hero 2 | KPI card | ARPU | — | — |
| Hero 3 | KPI card | Revenue churn rate | — | — |
| Center-left | Vertical bar | Churn rate | By contract | — |
| Center-right | Vertical bar | Churn rate | By internet service | — |
| Bottom (full-width) | Bubble scatter | Churn rate × ARPU, bubble = share of base | By segment | — |

**Default time range:** Same snapshot-date stamp as Page 1 — no range
picker.
**Sticky filters:** None on Page 2 by design — it is the fixed exec summary,
not an exploration surface (see anti-requirements).

---

## Interactivity

| Feature | Required | Notes |
|---|---|---|
| Date range filter | No | Snapshot dataset — replaced by a static "data as of [batch date]" stamp (see Layout) |
| Risk-band filter | Yes | Options: High / Medium / Low, default = All. Sticky, Page 1 only |
| Contract-type filter | Yes | Options: Month-to-month / One year / Two year, default = All. Sticky, Page 1 only |
| Internet-service filter | Yes | Options: DSL / Fiber optic / No, default = All. Sticky, Page 1 only |
| Segment filter | Yes | Options: the 3 named k-means segments, default = All. Sticky, Page 1 only |
| Drill-down: call-list row → Customer Detail | Yes | Click a row in the ranked table → opens a single-customer detail panel: full service profile, risk score, top 3 drivers, tenure, historical note field (retention leads log call outcomes here — see governance note below) |
| Drill-down: bottom-left bar (contract × band) → filtered call list | Yes | Click a bar segment → applies that contract+band combination as the sticky filter on the main table above it |
| Cross-filter | Yes, Page 1 only | Bottom-left and bottom-right bars both filter the main table; they do not filter each other (avoids filter-loop confusion) |
| Export / download | Yes | CSV export of the currently filtered call list — this is the literal deliverable the intake interview asked for ("something my team can sort and work top-down") |
| Alerts | Yes | See below |

**Alert thresholds:**

| Alert | Condition | Recipient | Channel |
|---|---|---|---|
| MRR-at-risk spike | MRR at risk (High band) increases >15% month-over-month | VP of Customer Retention | Email, monthly batch |
| New high-risk cohort | Count of customers newly entering the High band this batch > 200 | Retention team leads | Email, monthly batch |
| Batch scoring failure/staleness | "Data as of" date is >35 days old (batch didn't refresh) | Data Science team | Email + dashboard banner |

Thresholds are set at round, defensible levels the VP can sanity-check
without a statistics background, consistent with the skill's operational
(not strategic) decision classification from the intake interview — directional
correctness over precision.

---

## Access and governance

**Access level:** Team-only (retention org + VP + analytics). Not public —
customer-level PII (implicit via CustomerID + service profile) is present.
**Sensitive data present:** Yes — individual customer records with billing
amounts and service details. No name/address/SSN fields exist in the source
CSV, but CustomerID is a persistent identifier and MonthlyCharges/TotalCharges
are financial data.
**Row-level security needed:** No — this is a single-line residential book
with one retention team; no regional/BU split exists in the data to
partition on. (Documented as "no" rather than skipped, per the requirements
guide's explicit row-level-security question.)
**Who approves access requests:** VP of Customer Retention.

---

## Data and infrastructure

**BI tool:** Not mandated by the stakeholder; recommend a lightweight
self-service tool (e.g. Metabase or Looker Studio) given the modest metric
count and single data source — a full Tableau/Looker semantic-layer buildout
is disproportionate to an 11-metric, single-table dashboard.
**Connection:** Batch-scored output table joining `stg_telco_customers` +
model artifact scores (see below) — not a live warehouse connection, since
scoring is monthly-batch, not real-time.
**Refresh schedule:** Monthly, tied to the retention team's existing monthly
outreach cycle (per the intake interview). The model batch-scoring job must
complete and land its output table before the dashboard refresh runs.
**Data owner sign-off:** Pending — VP of Customer Retention has not yet
formally signed off on this spec (see checklist below); this document is the
artifact to take to that conversation.

---

## Anti-requirements (explicit exclusions)

Stated up front so a builder does not scope-creep the dashboard, per the
skill's "justify every filter/drill-down" and "resist putting level-3
content at level 1" guidance:

- **No real-time / streaming view.** The intake interview confirmed monthly
  batch is sufficient; a live-updating dashboard would be built for a
  requirement no one asked for.
- **No LTV:CAC or payback-period tile.** No acquisition-cost data exists in
  this dataset (documented gap in `semantic_model_telco.yml`'s `ltv` metric
  notes) — do not fabricate a CAC assumption to fill this tile.
- **No enterprise/business-account segment toggle.** This is a
  residential-only book; there is no enterprise line to filter to (per the
  intake interview's scope statement).
- **No date-range picker.** This is a cross-sectional snapshot with a
  monthly batch refresh, not a ledger — a date-range control would imply
  historical granularity the data doesn't have. Use the "data as of" stamp
  instead.
- **No sticky filters on Page 2.** The exec summary is meant to be a fixed,
  comparable-month-to-month view for the VP's own reporting up; letting it
  be filtered defeats that consistency and belongs on Page 1 instead.
- **No black-box risk score with no explanation.** The intake interview
  explicitly flagged "if it's a black box... this didn't answer my question"
  as a failure condition — the top-drivers column on the call list is not
  optional polish, it is a stated success criterion.
- **No more than 3 clusters/segments exposed as a filter.** The chosen
  k=3 segmentation (silhouette 0.3075) is the one already validated in
  `artifacts/segmentation_report.md`; do not re-expose k=2 or finer cuts
  here — that re-litigates a modeling decision already made in Phase 3.

---

## Acceptance criteria

- [ ] All metrics match definitions in `artifacts/semantic_model_telco.yml`
      (or are explicitly flagged as not-yet-modeled, per the Metrics table
      above)
- [ ] Default view (Page 1, All filters) loads in < 3 seconds — generous for
      an ~7K-row batch table, tight enough that retention leads won't
      abandon it
- [ ] Numbers cross-checked against `artifacts/business_metrics.json` and
      `artifacts/segment_profile_kmeans.csv` source output before first
      publish
- [ ] VP of Customer Retention has reviewed and signed off on this written
      spec (sign-off checklist below) before build starts
- [ ] Owner confirmed as a named role (VP of Customer Retention /
      Analytics team), not "analytics team" alone, per the template's own
      acceptance-criteria item

---

## Sign-off checklist (per `dashboard_requirements_guide.md`)

- [x] Primary question confirmed with the requester in writing — carried
      over from the Phase 1 intake interview transcript
- [x] All metrics have a written definition and a designated owner (table
      above; two rows flagged as pending Phase 4/5 model artifact, owner =
      Data Science)
- [ ] Data sources confirmed accessible with appropriate permissions —
      pending: model batch-scoring pipeline does not exist yet outside this
      lab's artifacts
- [x] Refresh cadence and acceptable lag agreed (monthly, ≤24h lag)
- [ ] Stakeholder confirmed they will use it — pending live conversation;
      simulated interview only establishes intent, not final commitment
- [x] Existing dashboards checked — none exist; this is a net-new capability
      per the Phase 1 intake

## Outputs produced

- `crisp_dm/06_deployment/dashboard-specification.md` (this document) — a
  complete, buildable spec per `assets/dashboard_spec_template.md`'s
  sections, with every metric traced to `artifacts/semantic_model_telco.yml`
