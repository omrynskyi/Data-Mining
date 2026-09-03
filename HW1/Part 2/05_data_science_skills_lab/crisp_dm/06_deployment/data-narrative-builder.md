---
skill: data-narrative-builder
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts: [artifacts/executive_summary.md]
---

## What the skill prescribes

1. Identify the single central message — if there's more than one, there are multiple
   presentations.
2. Choose a narrative framework (Situation-Complication-Resolution fits most problem/solution
   stories; Before-After-Bridge fits impact demonstrations).
3. Assign an emotional arc per section — comfort, then tension, then confidence.
4. Draft with the pyramid principle: conclusion first, then evidence; numbers serve the story.
5. Plan one visual per narrative beat.
6. Write a hook that earns attention in under 10 seconds and a CTA naming a specific decision,
   person, and deadline.

## Applied to Telco churn

**Central message** (one, per the skill's rule): *"We know exactly which quarter of our
customers is about to leave and why — approve a $35K campaign that returns $43K in the next
retention cycle."* Everything else in the story below is supporting material for this one claim.

**Framework chosen: Situation-Complication-Resolution.** This is a problem the business already
knows exists (churn) with a resolution being proposed now (the model + campaign) — SCR fits
better than Before-After-Bridge, which is stronger when a *change has already happened* and
needs to be shown as impact; here the ask is forward-looking, not retrospective.

| Beat | Content | Emotional target | Visual |
|---|---|---|---|
| **Hook** | "We're losing 30.5% of our revenue to churn — not 26.5% of our customers, 30.5% of the *money*, because the customers leaving are our highest-value ones." | Alarm, in under 10 seconds | Single stat card: 30.5% revenue churn vs 26.5% logo churn |
| **Situation** | Establish scale and where it concentrates: MRR at risk ($139K realized + $136K forward-looking), the Contract-type gradient (42.7% → 2.8%) | Comfort — this is measured, not guessed | `reports/figures/p2_target_distribution.png` + churn-by-contract bar |
| **Complication** | Two tempting stories are dead ends (gender, phone service — no effect); the real driver (contract + fiber service) requires a different kind of action than a generic "retention email" | Tension — the easy answer is wrong | Cramér's V ranking chart |
| **Resolution** | The model ranks risk well enough to fund a profitable, capacity-bounded campaign: 50% capacity, 46.5% precision, $43K net value | Confidence — there is a costed, bounded plan | Lift/gains chart (`reports/figures/p5_lift_gains.png`) |
| **CTA** | Approve $35,250/cycle for the retention-team lead, by the next monthly planning cycle, with a 60-day checkpoint | Decisive close | Decision-block table from `executive_summary.md` |

**Numbers serve the narrative, not the reverse**: large figures are rounded for recall in the
spoken/slide version ("$43K", "30% of revenue", "1 in 3 fiber customers") while the full-
precision numbers stay in the written backup (`executive_summary.md`,
`business_expected_value.json`) — the skill's guidance to humanize rather than dump precision
in a live narrative, while keeping the precise version available for anyone who asks.

**Where this narrative and the exec summary differ on purpose**: the executive summary
(`executive-summary-generator.md`) is the leave-behind document — dense, ranked, scannable in
one pass. This narrative is the *spoken/presented* arc — one message, a deliberate emotional
sequence, and a visual assigned to each beat — built to be delivered in a room, not read at a
desk. Reusing the same underlying numbers for both was a deliberate choice (one source of
truth), but the shape of the two documents is intentionally different, not a duplicate.

## Outputs produced

- The SCR narrative structure above (framework, beat-by-beat content, emotional arc, visual
  assignments) — the actual presentation-delivery artifact for this skill.
- Reuses `artifacts/executive_summary.md` as its numeric backup/leave-behind, not as a duplicate
  deliverable.
