---
skill: stakeholder-requirements-gathering
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 1 - Business Understanding
artifacts: []
---

# Stakeholder Requirements Gathering — Telco Customer Churn

## What the skill prescribes

- Run an intake interview (`assets/interview_guide.md`) to surface the business decision, audience, success criteria, and constraints.
- Classify the decision type (strategic / operational / tactical) using `references/decision_maker_framework.md` to calibrate rigour, format, and speed.
- Document requirements in `assets/requirements_doc_template.md`: business question, success criteria, scope in/out, data sources, timeline.
- Resolve ambiguities with elicitation techniques (`references/elicitation_techniques.md`) — 5-whys, scenario walkthrough, MoSCoW, the anti-requirements question.
- Get explicit sign-off from the requestor before starting work.
- Convert the approved requirements into a one-page `assets/analysis_brief_template.md` — the authoritative scope document.

## Applied to Telco churn

### Intake interview

**[simulated stakeholder input]** — VP of Customer Retention, telecom subscription business.

> **What's the business situation?** "We're losing about a quarter of our subscriber base over their lifetime and it's eating into recurring revenue. We don't have a systematic way to know *who* is about to leave before they leave."
>
> **What decision does this inform?** "Every month, my retention team picks accounts to call, offer discounts to, or proactively support. Right now they work off gut feel and a few manual SQL filters. I want a ranked list telling them who to call first."
>
> **What would a perfect output look like?** "A monthly list: customer ID, a churn-risk score, and a reason or two why. Something my team can sort and work top-down."
>
> **Who sees this?** "My retention team leads directly use the list. I want a monthly summary — revenue at risk, top drivers — for my own reporting up to the COO."
>
> **What would make you say 'this didn't answer my question'?** "If it's a black box with no explanation, or if it doesn't tell me the dollar impact, not just a churn percentage."
>
> **Segments to include/exclude?** "All residential customers. We don't have a separate enterprise line in this dataset, so no segment exclusion needed here."
>
> **Known data issues?** "Not that I know of — this is the first time we've tried to model this systematically."
>
> **Deadline?** "This is a recurring capability, not a one-off report — I'd like a first working version within this course's project timeline, refined over the six analysis phases."

**Root question surfaced via 5-whys (`elicitation_techniques.md` Technique 1):**
Stated ask: *"Can you tell me which customers are going to churn?"*
→ Why? "So we can call them before they leave."
→ Why do you need a call list specifically? "So retention agents don't waste time on customers who'd stay anyway."
→ Why does that matter? "Limited agent hours — we want the highest expected-value calls first."
→ **Root question:** *Which active customers have the highest churn probability and, among those, which represent the most revenue at risk — so a resource-constrained retention team can prioritize outreach?*

This reframes the ask from a binary churn label to a **ranked, revenue-weighted risk list** — materially different scope than "predict churn yes/no."

### Decision-type classification (`decision_maker_framework.md`)

| Field | Value |
|---|---|
| **Decision type** | **Operational** — the monthly risk list optimizes an existing retention workflow; each month's list is revisited and is highly reversible (a missed call this month is recoverable next month). |
| **Decider** | VP of Customer Retention |
| **Approver** | N/A for this lab (VP is decider and approver) |
| **Implementer** | Retention team leads (consume the ranked list directly) |
| **Required rigour** | Medium — directionally correct is sufficient; a well-calibrated ranking matters more than a perfect point-probability |
| **Required speed** | Medium — days, not weeks, once data is in hand; format: one-pager + ranked data export |
| **Format implication** | Ranked CSV/table + a one-page summary (not a formal board deck) — calibrated per the matrix in `decision_maker_framework.md` |

### Requirements document

*(filled from `assets/requirements_doc_template.md`)*

**Project / request name:** Telco Voluntary Churn Risk Scoring
**Requestor:** VP of Customer Retention [simulated stakeholder input]
**Primary analyst:** Data Science Skills Lab (this project)
**Date created:** 2026-09-02
**Target delivery date:** End of lab (all 6 CRISP-DM phases)
**Status:** Approved (simulated sign-off, see below)

**Business Question:**
> Which active customers have the highest probability of voluntary churn in the near term, and how much recurring revenue is at risk from each — so the retention team can prioritize monthly outreach?

**Decision This Informs:**
- Decision type: Operational
- Decider: VP of Customer Retention
- Decision deadline: Recurring (monthly), first version due at end of this lab
- Impact of delay: Retention team continues working off gut feel; revenue-at-risk exposure ($136,447.05/mo in active Month-to-month MRR alone — see `artifacts/business_metrics.json`) stays unaddressed.

**Success Criteria:**
1. Produces a churn-probability score (not just a binary label) per active customer.
2. Ranks customers so the top of the list represents the best expected retention value (risk × revenue), not just highest raw probability.
3. Includes a plain-language explanation of the top 2-3 risk drivers per customer or segment.
4. Reports aggregate revenue-at-risk in dollars, not just a churn rate.
5. Model performance and assumptions are documented well enough for a non-technical reviewer to trust the list (transparency requirement from the interview).

**Scope:**
- In scope: All 7,043 residential customers in `data/Telco-Customer-Churn.csv`; all contract types, all service lines.
- Out of scope: Enterprise/business accounts (not present in this dataset); real-time scoring (batch/monthly is sufficient per the interview); CAC/LTV:CAC-based prioritization (no acquisition-cost data available — documented gap).

**Data Sources:**

| Source | Table / system | Availability confirmed? |
|---|---|---|
| Telco customer snapshot | `data/Telco-Customer-Churn.csv` | Yes — downloaded, hashed, verified (`data/processed/dataset_meta.json`) |
| Train/test split | `data/processed/{train,test}.csv` | Yes — stratified, seed=42 |
| Acquisition cost / marketing spend | none | No — not available; LTV:CAC out of scope |

**Known data quality issues:** `TotalCharges` ships as text with 11 blank values (all `tenure == 0` customers, i.e. not yet billed) — must be coerced to numeric, not dropped silently.

**Output Format:**
- Format: Table/CSV (ranked risk list) + short Markdown report
- Delivery channel: Project deliverables under `crisp_dm/`
- Audience: Retention team leads (list) + VP (summary)
- Level of detail: Business-analyst detail for the summary; full technical detail available in the CRISP-DM phase docs for reviewers

**Assumptions and Constraints:**
- MonthlyCharges is treated as the customer's MRR contribution; tenure as months since acquisition (business framing set for the whole lab).
- This is a single cross-sectional snapshot, not a monthly ledger — "monthly churn rate" is an approximation, not a directly observed figure (see `artifacts/business_metrics.json`).

**Open Questions:**

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | Is a churn-probability threshold needed, or is a rank-ordered list sufficient? | VP | Resolved — rank-ordered is sufficient per interview |
| 2 | Should CAC data be sourced externally to enable LTV:CAC? | VP | Open — out of scope for this lab, logged as a data gap |

**Sign-off:** [simulated stakeholder input] — VP confirms this requirements document accurately describes the ask; analyst confirms feasibility given the available dataset and lab timeline.

### Analysis brief

*(one-page brief, `assets/analysis_brief_template.md`, derived from the requirements doc above)*

**The Question:** Which active customers have the highest churn probability and revenue at risk, ranked for monthly retention outreach?

**What "Done" Looks Like:**
1. Ranked, revenue-weighted churn-risk list per customer.
2. Top risk drivers explained in plain language.
3. Aggregate revenue-at-risk reported in dollars.

**Scope:**

| In scope | Out of scope |
|---|---|
| All 7,043 residential customers, all contract/service types | Enterprise accounts (not in dataset) |
| Batch/monthly scoring | Real-time scoring |
| Churn-probability ranking | LTV:CAC (no CAC data) |

**Data Plan:** `data/Telco-Customer-Churn.csv` (confirmed) → `data/processed/{train,test}.csv` (confirmed, stratified split).

**Approach (high level):** Follow the full 6-phase CRISP-DM plan (see `analysis-planning.md` in this folder) — business understanding → data understanding → data preparation → modeling → evaluation → deployment (ranked list generation).

**Output Format:** Ranked CSV/table + Markdown summary report.

**Constraints and Risks:** No CAC data (LTV:CAC out of scope); cross-sectional snapshot limits "monthly" metrics to approximations (documented throughout `artifacts/business_metrics.json`).

**Not In Scope (explicitly):** Enterprise segment, real-time scoring, CAC-based unit economics.

## Outputs produced

- This document — completed requirements doc + analysis brief, following `assets/requirements_doc_template.md` and `assets/analysis_brief_template.md`.
- Interview notes embedded above (intake interview + 5-whys root-question derivation).
- Decision-type classification per `references/decision_maker_framework.md`.
- No separate artifact files — this skill's outputs are the documentation itself (per the skill's own "Output" section, the requirements doc and brief *are* the deliverables).
