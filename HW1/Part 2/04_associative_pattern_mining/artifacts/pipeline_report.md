# CRISP-DM Pipeline Report: Associative Pattern Mining

**Run Timestamp**: `2026-09-03T05:45:03.256785Z`  
**Execution Duration**: `1.07s`  
**Dataset**: `online_retail_synthetic_fallback`  
**Algorithm**: `fpgrowth` (`auto`)  

---

## Executive Summary

An end-to-end CRISP-DM data mining pipeline was executed on **online_retail_synthetic_fallback**.
The pipeline cleaned `2,225` transactions across `55` products, discovering **244** frequent itemsets and **626** high-value association rules after redundancy pruning.

---

## Phase 1: Business Understanding
- **Primary Objective**: E-commerce market basket cross-sell discovery and catalog bundle optimization
- **Success Criteria / Target KPI**: Lift >= 1.2, Confidence >= 0.3, Zhang Metric > 0.0

## Phase 2: Data Understanding (EDA)
- **Raw Transactions**: `10,370` line items across `2,500` unique baskets
- **Catalog Size**: `81` unique products
- **Matrix Sparsity**: `91.99%` (Density: `8.01%`)
- **Cancellations / Returns**: `2.88%`

### Basket Size Distribution
| Statistic | Value |
| :--- | :--- |
| `min` | `0` |
| `q25` | `2.75` |
| `median` | `4.0` |
| `q75` | `5.0` |
| `max` | `14` |
| `mean` | `4.14` |
| `std` | `2.29` |
| `iqr` | `2.25` |
| `skewness` | `1.02` |

## Phase 3: Data Preparation
- **Cleaning Pipeline Steps Applied**:
  - `filter_negative_quantities_and_cancellations`
  - `strip_whitespace_and_normalize_descriptions`
  - `drop_null_descriptions`
  - `filter_administrative_stock_codes`
  - `filter_zero_or_negative_unit_prices`
  - `filter_single_item_baskets`
- **Cleaned Baskets**: `2,225`
- **One-Hot Matrix Shape**: `[2225, 55]`

## Phase 4: Modeling (Frequent Itemsets & Rule Mining)
- **Algorithm**: `fpgrowth` with `min_support=0.01`
- **Frequent Itemsets Found**: `244`
- **Raw Association Rules Extracted**: `796`

## Phase 5: Evaluation & Redundancy Pruning
- **Rules after Threshold Filtering**: `796`
- **Redundant Sub-Rules Pruned**: `170`
- **Final Actionable Rules**: `626`

### Rule Business Categories Breakdown
- **High-Lift Affinity Pair**: `516`
- **High-Confidence Cross-Sell**: `110`

---

## Top 10 Discovered Association Rules

| # | Antecedent | Consequent | Supp | Conf | Lift | Lev | Conv | Zhang | Kulc | IR | Cos | Cat |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `CERAMIC PLANT POT WHITE, ORGANIC POTTING SOIL 10L` | `GARDENING GLOVES PAIR, LED GROW LIGHT BULB` | 0.023 | 0.423 | 6.97 | 0.020 | 1.63 | 0.91 | 0.40 | 0.06 | 0.40 | High-Lift Affinity Pair |
| 2 | `GARDENING GLOVES PAIR, LED GROW LIGHT BULB` | `CERAMIC PLANT POT WHITE, ORGANIC POTTING SOIL 10L` | 0.023 | 0.385 | 6.97 | 0.020 | 1.54 | 0.91 | 0.40 | 0.06 | 0.40 | High-Lift Affinity Pair |
| 3 | `CERAMIC PLANT POT WHITE, ORGANIC POTTING SOIL 10L` | `LED GROW LIGHT BULB, WATERING CAN GREEN 2L` | 0.023 | 0.415 | 6.83 | 0.020 | 1.60 | 0.90 | 0.40 | 0.06 | 0.40 | High-Lift Affinity Pair |
| 4 | `LED GROW LIGHT BULB, WATERING CAN GREEN 2L` | `CERAMIC PLANT POT WHITE, ORGANIC POTTING SOIL 10L` | 0.023 | 0.378 | 6.83 | 0.020 | 1.52 | 0.91 | 0.40 | 0.06 | 0.40 | High-Lift Affinity Pair |
| 5 | `LED GROW LIGHT BULB, ORGANIC POTTING SOIL 10L, WATERING CAN GREEN 2L` | `CERAMIC PLANT POT WHITE` | 0.023 | 0.761 | 6.83 | 0.020 | 3.72 | 0.88 | 0.48 | 0.69 | 0.40 | High-Confidence Cross-Sell |
| 6 | `LARGE DESK PAD BLACK, MECHANICAL KEYBOARD, WIRELESS ERGONOMIC MOUSE` | `USB-C MULTIPORT ADAPTER` | 0.019 | 0.689 | 6.78 | 0.016 | 2.88 | 0.88 | 0.44 | 0.67 | 0.36 | High-Confidence Cross-Sell |
| 7 | `CERAMIC PLANT POT WHITE, ORGANIC POTTING SOIL 10L, WATERING CAN GREEN 2L` | `LED GROW LIGHT BULB` | 0.023 | 0.708 | 6.71 | 0.020 | 3.07 | 0.88 | 0.46 | 0.64 | 0.39 | High-Confidence Cross-Sell |
| 8 | `LED GROW LIGHT BULB, ORGANIC POTTING SOIL 10L` | `CERAMIC PLANT POT WHITE, WATERING CAN GREEN 2L` | 0.023 | 0.425 | 6.71 | 0.020 | 1.63 | 0.90 | 0.39 | 0.10 | 0.39 | High-Lift Affinity Pair |
| 9 | `CERAMIC PLANT POT WHITE, WATERING CAN GREEN 2L` | `LED GROW LIGHT BULB, ORGANIC POTTING SOIL 10L` | 0.023 | 0.362 | 6.71 | 0.020 | 1.48 | 0.91 | 0.39 | 0.10 | 0.39 | High-Lift Affinity Pair |
| 10 | `ORGANIC POTTING SOIL 10L, WATERING CAN GREEN 2L` | `CERAMIC PLANT POT WHITE, LED GROW LIGHT BULB` | 0.023 | 0.405 | 6.67 | 0.019 | 1.58 | 0.90 | 0.39 | 0.04 | 0.39 | High-Lift Affinity Pair |

---

## Phase 6: Deployment Artifacts
- `artifacts/pipeline_summary.json` (Machine-readable full CRISP-DM metadata)
- `artifacts/pipeline_report.md` (This executive summary report)
- `artifacts/rules.csv` (Mined association rules in tabular format)
- `artifacts/rules.json` (Mined association rules in JSON format for dashboard & API consumption)
- `artifacts/frequent_itemsets.csv` (All frequent itemsets with support and lengths)
