# Handoff Report: Requirement 1 (R1) — CRISP-DM Implementation & Data Processing

**Author**: Explorer Survey 1 (`explorer_survey_1`)  
**Mission**: Technical specification and architecture design for CRISP-DM Data Pipeline and Associative Pattern Mining.  
**Target Milestone**: Milestone 1 (M1) — CRISP-DM Pipeline & Pattern Mining Engine.  
**Date**: 2026-09-02  

---

## 1. Observation

### 1.1 Requirements Direct Quotes
From `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/ORIGINAL_REQUEST.md`:
- **R1. CRISP-DM Implementation & Data Processing**: *"The team must implement a data pipeline following the CRISP-DM framework, using a self-selected popular associative pattern mining dataset from Kaggle. The pipeline should handle data understanding, preparation, and modeling."*
- **Acceptance Criteria**:
  - *"- [ ] A `run_pipeline.py` script executes successfully end-to-end without manual intervention."*
  - *"- [ ] The pipeline outputs a summary artifact detailing the data preparation steps and the top discovered association rules."*

### 1.2 Environment & Platform Inspection
- **Python Runtime**: `Python 3.9.6` on macOS Darwin.
- **Available Base Libraries**: `pandas 2.3.3`, `scikit-learn 1.6.1`, `fastapi 0.115.6`, `uvicorn 0.34.0`, `numpy`, `scipy`.
- **Additional Dependency Requirements**: `mlxtend` (to be installed or backed by pure Python/NumPy dual engine), `matplotlib`, `seaborn`, `pytest`.

### 1.3 Kaggle Market Basket Dataset Survey
A review of top Kaggle associative pattern mining datasets identified four candidates:
1. **Online Retail Dataset (UCI / Kaggle)**:
   - **Schema**: `InvoiceNo` (str/int), `StockCode` (str), `Description` (str), `Quantity` (int), `InvoiceDate` (datetime), `UnitPrice` (float), `CustomerID` (float), `Country` (str).
   - **Scale**: 541,909 rows, ~25,900 invoices, ~4,070 unique products.
   - **Characteristics**: Real UK giftware transactions (2010–2011). Contains realistic anomalies (cancellations `C...`, discounts, postage, missing customer IDs). Considered the gold standard benchmark in retail data science.
2. **Groceries Dataset (Kaggle)**:
   - **Schema**: `Member_number`, `Date`, `itemDescription` (or transaction item lists).
   - **Scale**: 38,765 rows, 167 items.
   - **Characteristics**: Very clean, lightweight supermarket transactions.
3. **The Bread Basket Bakery Dataset (Edinburgh Bakery, Kaggle)**:
   - **Schema**: `Transaction`, `Item`, `date_time`, `period_day`, `weekday_weekend`.
   - **Scale**: 20,507 rows, 9,465 transactions, 94 unique items.
4. **Instacart Market Basket Analysis (Kaggle)**:
   - **Scale**: 3M+ orders, multi-table relational schema (>200MB). Overkill for rapid pipeline iterations and fast unit testing.

---

## 2. Logic Chain

1. **Dataset Selection Decision**:
   - **Primary Selected Dataset**: **Online Retail II / Online Retail (Kaggle)**.
     - *Rationale*: It provides rich real-world complexities (returns, prices, temporal dimensions, multiple countries) essential for demonstrating the full breadth of CRISP-DM Data Understanding and Data Preparation.
   - **Multi-Dataset Adapter & Synthetic Generator Support**:
     - To ensure zero-friction offline execution and robust testability, the data loader must support:
       1. `online_retail` (default)
       2. `groceries`
       3. `bakery`
       4. `synthetic` (a deterministic, realistic retail transaction generator with planted association rules for offline CI/CD and rapid regression testing).

2. **CRISP-DM 6-Phase Architecture Mapping**:
   - **Phase 1: Business Understanding**:
     - Translates business objectives (Average Order Value lift, cross-sell recommendation, catalog bundling, store shelf placement) into mathematical association mining targets ($supp \ge s_{min}, conf \ge c_{min}, lift \ge l_{min}$).
   - **Phase 2: Data Understanding**:
     - Computes distribution metrics: transaction length / basket size (mean, median, IQR, max), item popularity Pareto distribution (Zipfian decay), matrix density/sparsity, missing value profiles, and cancellation/return rates.
   - **Phase 3: Data Preparation**:
     - Cleans product descriptions, filters out administrative codes (`POST`, `D`, `M`, `BANK CHARGES`), removes canceled/negative quantity orders, handles unit price anomalies, filters single-item transactions ($|basket| < 2$), and transforms transactions into a boolean one-hot / sparse matrix using `TransactionEncoder` or vectorized sparse pivots.
   - **Phase 4: Modeling**:
     - Implements both **Apriori** and **FP-Growth** algorithms.
     - Generates frequent itemsets and decomposes them into association rules ($A \implies C$).
     - Computes comprehensive interest metrics: Support, Confidence, Lift, Leverage, Conviction, Zhang's metric, Kulczynski, Imbalance Ratio, and Cosine.
     - Provides dual-engine capability (`mlxtend` + zero-dependency native custom engine) for maximum portability.
   - **Phase 5: Evaluation**:
     - Filters rules by multi-metric criteria, removes redundant sub-rules ($A \subset A' \land conf(A') \le conf(A)$), computes a composite multi-criteria ranking score, and categorizes rules into actionable business clusters (High-Confidence Cross-Sells, High-Lift Affinity Pairs, Emerging Niche Bundles, Dissociated Pairs).
   - **Phase 6: Deployment**:
     - Exports structured summary artifacts (`pipeline_summary.json`, `pipeline_report.md`, `rules.csv`, `rules.json`, `frequent_itemsets.csv`, and `pipeline_state.pkl`) consumed seamlessly by R2 (Hill Climbing) and R3 (Admin Dashboard).

3. **`run_pipeline.py` CLI & Pipeline Execution Flow**:
   - Must be executable with zero arguments using robust defaults: `python run_pipeline.py`.
   - Must provide flexible CLI flags: `--dataset`, `--algorithm`, `--min-support`, `--min-confidence`, `--metric`, `--min-metric-val`, `--max-len`, `--country`, `--output-dir`, `--generate-synthetic`, `--engine`, `--quiet`.
   - Must run synchronously, exit with status code 0, and output cleanly formatted execution metrics.

---

## 3. Caveats & Edge Cases

1. **Infinite Conviction**:
   - When a rule has 100% confidence ($conf(A \to C) = 1.0$), $1 - conf = 0$, leading to $conviction = \infty$.
   - *Mitigation*: Cap conviction at `100.0` or format properly as `null` / `inf` handling in JSON export to prevent serialization errors.
2. **Matrix Sparsity & Memory Consumption**:
   - In datasets with >10,000 products, dense boolean matrices can consume gigabytes of RAM.
   - *Mitigation*: Utilize `scipy.sparse.csr_matrix` or pandas `SparseDtype("bool")` during one-hot encoding, and filter long-tail infrequent items early before matrix expansion.
3. **Cancellations and Returns**:
   - In Online Retail, `InvoiceNo` starting with `'C'` and negative `Quantity` represent returns. If not separated, they could falsely distort basket associations.
   - *Mitigation*: Dedicated cleaning function `filter_returns_and_cancellations()` separates or drops return transactions for basket affinity mining while logging return statistics in Phase 2 EDA.
4. **Single-Item Baskets**:
   - Invoices with only 1 line item cannot produce association rules ($|A \cup C| \ge 2$).
   - *Mitigation*: Filter out single-item baskets during Data Prep, while recording the single-item ratio in Data Understanding.
5. **Missing Customer IDs**:
   - In Online Retail, ~25% of transactions have `NaN` for `CustomerID` (guest checkouts).
   - *Mitigation*: Basket grouping is performed on `InvoiceNo`, not `CustomerID`, so transactions without `CustomerID` remain valid for basket mining.

---

## 4. Conclusion & Technical Specification

### 4.1 Project Directory & Module Layout
```
04_associative_pattern_mining/
├── data/
│   ├── raw/
│   │   ├── online_retail.csv
│   │   └── groceries.csv
│   └── generate_synthetic.py       # Deterministic realistic retail data seeder
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py               # Multi-dataset loader (retail, groceries, bakery, synthetic)
│   │   ├── preprocessor.py         # Cleaning, filtering, aggregation, one-hot encoding
│   │   └── schema.py               # Data models & validation schemas
│   ├── eda/
│   │   ├── __init__.py
│   │   └── profiler.py             # Data Understanding profiler (basket sizes, sparsity, Zipf)
│   ├── mining/
│   │   ├── __init__.py
│   │   ├── engine.py               # Unified mining facade
│   │   ├── apriori.py              # Apriori frequent itemset algorithm
│   │   ├── fpgrowth.py             # FP-Growth frequent itemset algorithm
│   │   ├── rules.py                # Association rule extractor
│   │   └── metrics.py              # Mathematical metric calculations (Support, Conf, Lift, Zhang...)
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── filter.py               # Threshold filtering & interest scoring
│   │   └── redundancy.py           # Redundant rule pruning
│   ├── deployment/
│   │   ├── __init__.py
│   │   ├── exporter.py             # JSON, CSV, and Markdown artifact generators
│   │   └── pipeline.py             # End-to-end CRISP-DM pipeline runner
│   └── utils/
│       ├── __init__.py
│       ├── logger.py               # Structured terminal/file logger
│       └── timer.py                # Execution timing utilities
├── artifacts/                      # Output directory for pipeline results
│   ├── pipeline_summary.json       # Machine-readable summary
│   ├── pipeline_report.md          # Human-readable markdown report
│   ├── rules.csv                   # Discovered association rules
│   ├── rules.json                  # Discovered association rules in JSON
│   └── frequent_itemsets.csv       # Frequent itemsets
├── run_pipeline.py                 # CLI entrypoint for R1 CRISP-DM pipeline
├── requirements.txt                # Python package dependencies
└── tests/
    ├── test_data_loader.py
    ├── test_preprocessor.py
    ├── test_eda_profiler.py
    ├── test_mining_algorithms.py
    ├── test_rule_metrics.py
    ├── test_pipeline_e2e.py
    └── test_artifacts.py
```

### 4.2 Association Metric Mathematical Definitions
| Metric | Mathematical Formula | Range | Interpretation |
| :--- | :--- | :--- | :--- |
| **Support ($supp$)** | $P(A \cup C) = \frac{\sigma(A \cup C)}{N}$ | $[0, 1]$ | Frequency of co-occurrence in all transactions |
| **Confidence ($conf$)** | $P(C \mid A) = \frac{supp(A \cup C)}{supp(A)}$ | $[0, 1]$ | Conditional probability of $C$ given $A$ |
| **Lift ($lift$)** | $\frac{conf(A \to C)}{supp(C)} = \frac{P(A \cup C)}{P(A)P(C)}$ | $[0, \infty)$ | Ratio of observed co-occurrence vs independence ($>1$: positive affinity) |
| **Leverage ($lev$)** | $supp(A \cup C) - supp(A)supp(C)$ | $[-0.25, 0.25]$ | Difference between observed and expected support |
| **Conviction ($conv$)** | $\frac{1 - supp(C)}{1 - conf(A \to C)}$ | $[0, \infty)$ | Implication strength (frequency of rule error if independent vs actual) |
| **Zhang's Metric** | $\frac{supp(AC) - supp(A)supp(C)}{\max(supp(AC)(1 - supp(A)), supp(A)(supp(C) - supp(AC)))}$ | $[-1, 1]$ | Bounded measure of positive ($>0$) vs negative ($<0$) association |
| **Kulczynski ($kulc$)** | $\frac{1}{2} \left( conf(A \to C) + conf(C \to A) \right)$ | $[0, 1]$ | Null-invariant average conditional probability |
| **Imbalance Ratio ($IR$)** | $\frac{\lvert supp(A) - supp(C) \rvert}{supp(A) + supp(C) - supp(AC)}$ | $[0, 1]$ | Imbalance between antecedent and consequent itemset support |
| **Cosine** | $\frac{supp(A \cup C)}{\sqrt{supp(A) \cdot supp(C)}}$ | $[0, 1]$ | Geometric mean of both directional confidences |

### 4.3 CLI Interface Specification for `run_pipeline.py`
```bash
python run_pipeline.py [OPTIONS]

Options:
  --dataset TEXT          Dataset name or path ('online_retail', 'groceries', 'bakery', 'synthetic', or filepath) [default: online_retail]
  --algorithm TEXT        Frequent itemset algorithm ('fpgrowth', 'apriori', 'both') [default: fpgrowth]
  --min-support FLOAT     Minimum support threshold (0.001 - 1.0) [default: 0.01]
  --min-confidence FLOAT  Minimum confidence threshold (0.0 - 1.0) [default: 0.3]
  --metric TEXT           Primary metric for rule filtering ('lift', 'confidence', 'support', 'zhangs_metric') [default: lift]
  --min-metric-val FLOAT  Minimum threshold value for the primary metric [default: 1.2]
  --max-len INTEGER       Maximum length of frequent itemsets [default: 4]
  --country TEXT          Filter transactions by country (e.g. 'United Kingdom', 'France', 'all') [default: all]
  --output-dir TEXT       Directory to write pipeline artifacts [default: artifacts]
  --generate-synthetic    Flag to force generation of synthetic dataset if raw data is absent [default: True if raw missing]
  --engine TEXT           Algorithm engine ('auto', 'mlxtend', 'custom') [default: auto]
  --prune-redundant       Enable pruning of redundant sub-rules [default: True]
  --quiet / --verbose     Control terminal logging verbosity
  --help                  Show help message and exit
```

### 4.4 `pipeline_summary.json` Output Schema
```json
{
  "pipeline_metadata": {
    "run_timestamp": "2026-09-02T17:30:00Z",
    "execution_time_seconds": 1.42,
    "framework": "CRISP-DM",
    "dataset_name": "online_retail",
    "algorithm": "fpgrowth",
    "engine": "mlxtend_with_custom_metrics",
    "parameters": {
      "min_support": 0.01,
      "min_confidence": 0.3,
      "primary_metric": "lift",
      "min_metric_val": 1.2,
      "max_len": 4,
      "country": "all"
    }
  },
  "crisp_dm_stages": {
    "business_understanding": {
      "objective": "E-commerce basket cross-sell discovery and product bundle optimization",
      "target_kpi": "Lift > 1.2, Confidence > 0.3, Zhang Metric > 0.5"
    },
    "data_understanding": {
      "raw_records_count": 541909,
      "unique_invoices": 25900,
      "unique_items": 4070,
      "unique_customers": 4372,
      "cancellation_rate_pct": 1.83,
      "sparsity_pct": 99.82,
      "basket_size_stats": {
        "min": 1,
        "q25": 2,
        "median": 5,
        "q75": 12,
        "max": 180,
        "mean": 8.41,
        "std": 9.12
      },
      "top_5_frequent_items": [
        {"item": "WHITE HANGING HEART T-LIGHT HOLDER", "count": 2369, "frequency": 0.091},
        {"item": "REGENCY CAKESTAND 3 TIER", "count": 2200, "frequency": 0.085}
      ]
    },
    "data_preparation": {
      "cleaning_steps_applied": [
        "strip_whitespace_and_normalize_descriptions",
        "drop_null_descriptions",
        "filter_administrative_codes",
        "filter_negative_quantities_and_cancellations",
        "filter_zero_or_negative_unit_prices",
        "filter_single_item_baskets"
      ],
      "cleaned_transactions_count": 19820,
      "cleaned_unique_items_count": 3840,
      "matrix_shape": [19820, 3840],
      "matrix_density_pct": 0.28
    },
    "modeling": {
      "frequent_itemsets_total": 412,
      "itemsets_by_length": {
        "k=1": 180,
        "k=2": 198,
        "k=3": 34
      },
      "raw_rules_generated": 284
    },
    "evaluation": {
      "rules_after_threshold_filtering": 142,
      "redundant_rules_pruned": 18,
      "final_actionable_rules_count": 124,
      "rule_categories": {
        "high_confidence_cross_sells": 45,
        "high_lift_affinity_pairs": 62,
        "emerging_niche_bundles": 17
      }
    },
    "deployment": {
      "artifacts_generated": [
        "artifacts/pipeline_summary.json",
        "artifacts/pipeline_report.md",
        "artifacts/rules.csv",
        "artifacts/rules.json",
        "artifacts/frequent_itemsets.csv"
      ]
    }
  },
  "top_rules": [
    {
      "antecedents": ["ALARM CLOCK BAKELIKE GREEN"],
      "consequents": ["ALARM CLOCK BAKELIKE RED"],
      "support": 0.0312,
      "confidence": 0.684,
      "lift": 13.24,
      "leverage": 0.0288,
      "conviction": 3.01,
      "zhangs_metric": 0.942,
      "kulczynski": 0.648,
      "imbalance_ratio": 0.082,
      "cosine": 0.647
    }
  ]
}
```

### 4.5 Dependencies (`requirements.txt`)
```
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
mlxtend>=0.22.0
matplotlib>=3.7.0
seaborn>=0.12.0
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
pytest>=7.3.0
pytest-cov>=4.1.0
```

---

## 5. Verification Method

To independently verify the implementation when built:

1. **End-to-End Pipeline Execution**:
   ```bash
   python run_pipeline.py --dataset synthetic --algorithm fpgrowth --output-dir artifacts
   ```
   *Expected Outcome*: Script completes with exit code 0, outputs detailed CRISP-DM execution logs, and creates valid `artifacts/pipeline_summary.json` and `artifacts/pipeline_report.md`.

2. **JSON Schema & Artifact Verification**:
   ```bash
   python -c "import json; data=json.load(open('artifacts/pipeline_summary.json')); assert data['crisp_dm_stages']['modeling']['frequent_itemsets_total'] > 0; assert len(data['top_rules']) > 0; print('Summary Artifact Verified OK')"
   ```

3. **Algorithm & Metric Unit Testing**:
   ```bash
   pytest tests/test_mining_algorithms.py tests/test_rule_metrics.py -v
   ```
   *Expected Outcome*: Validates that Apriori and FP-Growth yield identical frequent itemsets, and that Support, Confidence, Lift, Leverage, Conviction, and Zhang's metric match ground-truth mathematical formulas.

4. **CLI Argument Variation Test**:
   ```bash
   python run_pipeline.py --algorithm apriori --min-support 0.02 --min-confidence 0.4 --metric zhangs_metric --min-metric-val 0.5
   ```
   *Expected Outcome*: Pipeline parses arguments cleanly, filters rules by Zhang's metric, and regenerates updated summary artifacts.
