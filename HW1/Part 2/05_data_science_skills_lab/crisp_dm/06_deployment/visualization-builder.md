---
skill: visualization-builder
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - src/p6_visualization.py
  - reports/figures/p6_churn_by_contract.png
  - reports/figures/p6_funnel_dropoff.png
  - reports/figures/p6_segment_value_risk_bubble.png
  - reports/figures/p6_tenure_survival.png
  - reports/figures/p6_before_bad_chart.png
  - reports/figures/p6_after_redesigned_chart.png
  - artifacts/p6_visualization_manifest.json
---

# Visualization Builder — Telco Churn Retention Program

## What the skill prescribes

`.claude/skills/visualization-builder/SKILL.md` defines a six-step process:
identify the message type (comparison / trend / composition / distribution /
relationship) before picking a chart type; aggregate data to the right grain
*before* it hits the chart library; build with pre-set professional styling
(whitegrid, sans-serif, accessible palette, `references/visual_design_principles.md`);
apply visual hierarchy so the one data element that matters is visually
dominant; write a title that states the finding, not the variable names;
export at 150 DPI for on-screen use and check the "five-second test."
`references/chart_selection_guide.md` gives a decision tree by message type
and an explicit "what to avoid" table (3D pie, dual y-axis, radar charts,
overlapping area fills).

## Applied to Telco churn

`src/p6_visualization.py` recomputes every number directly from
`data/Telco-Customer-Churn.csv` and the already-verified Phase 1-5 artifacts
(`funnel_results.json`, `segment_profile_kmeans.csv`,
`ts_hazard_by_tenure_month.csv`) — nothing plotted here is invented. A shared
Wong (2011) colour-blind-safe categorical palette and a `_title_block()`
helper (figure-level `suptitle` + `fig.text`, sized to the number of title
lines so multi-line finding-titles never collide with the subtitle) are used
across all six figures for visual consistency.

| # | Chart | Message type | Chart type chosen | Why (per chart_selection_guide.md) |
|---|---|---|---|---|
| 1 | Churn by contract | Comparison, 3 categories | Vertical bar | "Comparing discrete categories → bar. ≤7 bars." One bar (Month-to-month) is highlighted in vermillion because it is the dominant driver (42.71% vs 11.27%/2.83%); the other two stay neutral grey — one pre-attentive attribute (hue) isolates the focal point per `visual_design_principles.md`. |
| 2 | Service-adoption funnel | Sequential process, volume drop-off | Horizontal-bar funnel | "Sequential process with drop-off → funnel... label both absolute count and conversion rate for each step... highlight the step with the largest absolute drop-off." Matplotlib has no native funnel primitive, so a sorted horizontal bar substitutes (guide explicitly allows this framing). Churn rate is folded in as a **direct label**, not a second axis, per the "avoid dual y-axis" rule below. |
| 3 | Segment value × risk | Relationship between two continuous variables + a magnitude | Bubble scatter | "Relationship between two continuous variables → scatter plot... add a trend line if showing correlation." Bubble size (share of base) is a third dimension, which the guide flags as "hard to read accurately" — so exact share % and $ at risk are also given as a **direct label** next to each bubble rather than relying on size alone. |
| 4 | Tenure survival | Trend over a continuous dimension (tenure month) | Line + area fill | "Continuous time series → line... Y-axis should start at 0 for absolute values." Y-axis starts at 0%; a reference line marks the point the guide calls out for annotating "thresholds directly on the chart" (median-lifetime crossing, or final survival % if never crossed — here 59% at 72 months, so the latter). |
| 5a | BEFORE (deliberately bad) | Composition (3 categories) | Pseudo-3D exploded/shadowed pie **+ inset dual axis** | Built to violate two explicit "avoid" rules simultaneously: "3D bar/pie: depth distorts relative sizes" and "Dual y-axis: creates false correlation impression." Title ("Internet Service") also violates the annotation rule (finding, not variable name). |
| 5b | AFTER (redesign) | Comparison, 3 categories | Sorted horizontal bar | Same chart-selection rule as #1/#2. The second metric (avg MonthlyCharges) and churn rate are folded into one direct label per bar instead of a second axis; the bar with the discordant finding (fiber pays the most *and* churns the most) is highlighted in vermillion; title states the finding. |

**Accessibility applied throughout:** Wong colour-blind-safe hues only
(blue `#0072B2`, vermillion `#D55E00`, teal `#009E73`, grey neutrals); never
red-green as a good/bad pair; direct data labels instead of legends wherever
there is a small number of series (per `visual_design_principles.md`'s "legend
when direct labels are possible = noise" rule); one highlighted colour per
chart, not decorative variety; source/date footer on every chart; grid lines
kept at 0.25 alpha, no chart borders, top/right spines removed.

**Five-second test**, self-applied to each chart: title alone states the
finding (e.g. "Month-to-month customers churn 15x more than two-year
customers"); the single highlighted bar/point is the first thing the eye
lands on; the chart is legible in greyscale because the highlight also
carries a distinct hatch-free fill and every key value is a direct numeric
label, not colour-only encoding.

**Gains/lift chart:** not produced. `artifacts/final_metrics.json` (the
Phase 4/5 modeling output a gains/lift chart depends on) did not exist at
the time this skill ran — checked directly (`ls artifacts/final_metrics.json`
→ not found). This is noted rather than fabricated; if Phase 4/5 completes
later, a gains/lift chart can be added by re-running with the same
`_title_block` styling helpers already in `src/p6_visualization.py`.

## Outputs produced

- `src/p6_visualization.py` — the chart-generation script (matplotlib Agg
  backend, 130 DPI, run standalone: `python3 src/p6_visualization.py`)
- `reports/figures/p6_churn_by_contract.png`
- `reports/figures/p6_funnel_dropoff.png`
- `reports/figures/p6_segment_value_risk_bubble.png`
- `reports/figures/p6_tenure_survival.png`
- `reports/figures/p6_before_bad_chart.png` (deliberately bad, for contrast)
- `reports/figures/p6_after_redesigned_chart.png` (the fix)
- `artifacts/p6_visualization_manifest.json` — machine-readable record of
  what each chart shows and the exact rule citations used to choose it
