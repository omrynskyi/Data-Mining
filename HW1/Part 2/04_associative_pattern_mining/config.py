"""
Global Configuration & Path Constants for Associative Pattern Mining.
"""

from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
TESTS_DIR = PROJECT_ROOT / "tests"

# Ensure essential directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Synthetic Dataset Configuration
SYNTHETIC_DATA_PATH = RAW_DATA_DIR / "synthetic_retail.csv"
SYNTHETIC_DEFAULT_INVOICES = 2500
SYNTHETIC_RANDOM_SEED = 42

# Default Mining Hyperparameters
DEFAULT_MIN_SUPPORT = 0.01
DEFAULT_MIN_CONFIDENCE = 0.3
DEFAULT_PRIMARY_METRIC = "lift"
DEFAULT_MIN_METRIC_VAL = 1.2
DEFAULT_MAX_LEN = 4
DEFAULT_ALGORITHM = "fpgrowth"
DEFAULT_ENGINE = "auto"  # 'auto', 'mlxtend', 'custom'
DEFAULT_COUNTRY = "all"

# Supported Datasets
SUPPORTED_DATASETS = {
    "online_retail": RAW_DATA_DIR / "online_retail.csv",
    "groceries": RAW_DATA_DIR / "groceries.csv",
    "bakery": RAW_DATA_DIR / "bakery.csv",
    "synthetic": SYNTHETIC_DATA_PATH,
}

# Metric Names & Descriptions
METRIC_DEFINITIONS = {
    "support": "P(A ∪ C) - Itemset co-occurrence frequency across all transactions.",
    "confidence": "P(C | A) - Conditional probability of consequent given antecedent.",
    "lift": "P(A ∪ C) / (P(A) * P(C)) - Multiplier of co-occurrence over independence.",
    "leverage": "P(A ∪ C) - P(A) * P(C) - Difference between joint probability and expected independent probability.",
    "conviction": "(1 - P(C)) / (1 - P(C | A)) - Implication strength; capped at 100.0 for 100% confidence.",
    "zhangs_metric": "Bounded measure in [-1, 1] distinguishing positive association from negative association.",
    "kulczynski": "Average of conditional probabilities P(C|A) and P(A|C); null-invariant.",
    "imbalance_ratio": "Measures support asymmetry between antecedent and consequent itemsets.",
    "cosine": "Geometric mean of directional confidences sqrt(conf(A->C) * conf(C->A)).",
}

# Administrative Codes to exclude during Retail Data Cleaning
ADMINISTRATIVE_STOCK_CODES = {
    "POST", "POSTAGE", "D", "M", "MANUAL", "BANK CHARGES",
    "AMAZON FEE", "DOT", "DOTCOM", "CRUK", "SAMPLES", "PADS", "ADJUST", "ADJUST2"
}

# Conviction Infinity Cap
CONVICTION_MAX_CAP = 100.0
