---
skill: semantic-model-builder
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 1 - Business Understanding
artifacts: [artifacts/semantic_model_telco.yml]
---

# Semantic Model Builder — Telco Customer Churn

## What the skill prescribes

- Identify the object type being documented (metric, dimension, or entity) and use the matching framework (`references/metric_definition_framework.md` for metrics, `references/dimension_hierarchy_patterns.md` for dimensions).
- Gather definition inputs: calculation logic, business context, data source, grain, edge cases, gotchas.
- Scaffold the YAML with `scripts/metric_template_generator.py`.
- Validate with `scripts/model_yaml_validator.py` — required fields, type constraints, reference integrity.
- Consult `references/dbt_semantic_layer_guide.md` for exact dbt field names/constraints when targeting dbt Semantic Layer.
- Save final definitions to `assets/{metric,dimension,entity}_definition.yaml`.

## Applied to Telco churn

### Scaffolding (the skill's real generator script, actually run)

```
python3 .claude/skills/semantic-model-builder/scripts/metric_template_generator.py --type entity --name customer
python3 .claude/skills/semantic-model-builder/scripts/metric_template_generator.py --type dimension --name contract
python3 .claude/skills/semantic-model-builder/scripts/metric_template_generator.py --type metric --name mrr
```

Each call produced a `[REQUIRED]`-marked scaffold matching the skill's templates. Those scaffolds were filled in and merged into a single dbt-Semantic-Layer-style file rather than three separate template files, since a dbt semantic model natively nests entities/dimensions/measures under one `semantic_models:` block (per `references/dbt_semantic_layer_guide.md`) with a sibling top-level `metrics:` block — that's the layout used in `artifacts/semantic_model_telco.yml`.

### Object type framework applied

- **Entity** (`customer`) — primary entity, `expr: customer_id`, grain "one row per customer".
- **Dimensions** — `contract`, `internet_service`, `payment_method` (flat categorical, per `dimension_hierarchy_patterns.md`'s flat-dimension guidance, with documented `possible_values`); `tenure_bucket` (a **derived, bucketed** dimension — applies the skill's "High-Cardinality Dimensions" bucket-at-ingestion strategy to the continuous `tenure` column, range 0-72 months, verified from data); `acquired_at` — included as a **time dimension placeholder**, explicitly marked not-yet-backed-by-real-data (this snapshot has no acquisition date field), following the metric-definition-framework principle of documenting known gaps rather than fabricating a column.
- **Metrics** (`references/metric_definition_framework.md`'s 7 questions, answered for each): `mrr` (simple), `arpu` (ratio), `churn_rate` (ratio), `revenue_churn_rate` (ratio), `ltv` (derived). Each metric's `meta.calculation_notes` states grain, inclusions/exclusions, edge cases, and the **real computed value** from `artifacts/business_metrics.json`, per the framework's "What does good look like" and "known edge cases" questions.

### Validation (the skill's real validator script, actually run)

```
python3 .claude/skills/semantic-model-builder/scripts/model_yaml_validator.py \
  --input artifacts/semantic_model_telco.yml --strict
```

Output: `✓ artifacts/semantic_model_telco.yml is valid` — no missing required fields, no unfilled `[REQUIRED]` placeholders, no unknown metric types, in the top-level `metrics:` list.

**Caveat on validator coverage:** `model_yaml_validator.py` only inspects flat top-level `metrics:` / `dimensions:` / `entities:` lists. This file's `dimensions:` and `entities:` are nested inside `semantic_models:` (the correct real dbt Semantic Layer shape per `dbt_semantic_layer_guide.md`), so the validator only actually checked the `metrics:` block. A second, independent check was run to cover the whole file:

```python
import yaml
data = yaml.safe_load(open("artifacts/semantic_model_telco.yml"))
# -> parses cleanly: semantic_models[0] has entities=['customer'],
#    dimensions=['contract','internet_service','payment_method','tenure_bucket','acquired_at'],
#    measures=['monthly_charges_sum','monthly_charges_avg','customer_count',
#              'churned_customer_count','total_charges_avg'];
#    metrics=['mrr','arpu','churn_rate','revenue_churn_rate','ltv']
```

Both checks passed. Reference integrity was verified by inspection: every metric's `type_params` references either a `measure` defined in `telco_customers.measures` or, for the `derived` `ltv` metric, the `arpu` metric defined earlier in the same file — no dangling references.

### Metrics defined (mirrors real numbers in `artifacts/business_metrics.json` — see that file / `business-metrics-calculator.md` for full computation detail)

| Metric | Type | Formula | Real value |
|---|---|---|---|
| `mrr` | simple | `sum(monthly_charges)` | $456,116.60 |
| `arpu` | ratio | `monthly_charges_sum / customer_count` | $64.76 |
| `churn_rate` | ratio | `churned_customer_count / customer_count` | 26.537% |
| `revenue_churn_rate` | ratio | `churned MRR / total MRR` | 30.503% |
| `ltv` | derived | `arpu / monthly_churn_rate_hazard` | $7,899.96 (+ tenure-based variant $2,283.30, documented in `meta.calculation_notes`) |

## Outputs produced

- `artifacts/semantic_model_telco.yml` — full dbt-Semantic-Layer-compatible semantic model: 1 entity, 5 dimensions (incl. 1 derived/bucketed, 1 documented gap placeholder), 5 measures, 5 metrics — validated both by the skill's own validator and a plain YAML parse.
