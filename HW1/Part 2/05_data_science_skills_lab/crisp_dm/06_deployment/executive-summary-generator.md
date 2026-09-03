---
skill: executive-summary-generator
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts: [artifacts/executive_summary.md]
---

## What the skill prescribes

- Extract only the top 3-5 insights that change or reinforce a decision — filter out
  interesting-but-not-actionable findings.
- Quantify business impact for every insight (revenue, cost, users affected) — never "significant".
- One-paragraph situation statement: why this analysis, what question, why the timing matters.
- Pyramid principle: lead every insight with the conclusion, then evidence.
- Recommendations must name the action, owner, expected outcome, and deadline.
- Close with an explicit decision block: what approval, what it costs, what it returns, by when.

## Applied to Telco churn

`artifacts/executive_summary.md` is the packaged one-pager, built with the skill's own
`assets/executive_summary_template.md` structure (situation → ranked insights with impact →
recommendations table → decision block).

**5 insights selected, in decision-priority order** (not analysis order) — Contract type as the
strongest lever, the model's validated ability to fund a profitable campaign, the sized
$43K/cycle campaign, the fiber-optic anomaly, and the two negative findings (gender,
PhoneService) that kill wasted work. This is a deliberate cut from the ~15+ findings produced
across this lab's 42 other skill demonstrations — the skill's instruction "if you have more than
5 insights, you haven't prioritised yet" was followed literally, not treated as a suggestion.

**Every insight carries a number**, per the skill's hard requirement: 42.7% vs 2.8% (not "much
higher"), $43K net value with a stated range (not "profitable"), 41.9% vs 14.5% with the 78/22
decomposition (not "fiber customers churn more"), Cramér's V ≈0.01-0.02 for the negative
findings (not "doesn't seem to matter").

**Recommendations are actions, not aspirations**: each row of the table names a specific owner
(Retention team lead / Product owner / Analytics team / ML engineering), a concrete expected
outcome tied to a real number from this analysis, and a deadline tied to the business cycle —
matching the skill's explicit rejection of vague recommendations like "improve the app".

**Decision block** names the exact ask ($35,250/cycle budget approval), the exact return
($43K net value, cross-referenced to the confidence range in `impact-quantification.md`), and a
concrete checkpoint (60-day comparison of actual vs. budgeted 98.4 saves) rather than an
open-ended commitment.

**One deliberate departure from a "clean win" narrative**: the summary's closing section states
plainly that the Contract-churn relationship is observational, not causal, and names the A/B
test that should run before scaling — because an executive summary that hides a study's real
limitation to make the ask look cleaner produces a worse decision, not a better one.

## Outputs produced

- `artifacts/executive_summary.md` — the 1-page decision-ready summary.
