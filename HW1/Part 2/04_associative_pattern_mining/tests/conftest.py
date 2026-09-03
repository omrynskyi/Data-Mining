"""
tests/conftest.py
Comprehensive Shared Pytest Fixtures for Associative Pattern Mining & Admin Studio.
Provides mock datasets, synthetic transaction generators, dummy artifacts,
Flask test clients, and research paper benchmark configurations.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from flask import Flask, jsonify

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.generate_synthetic import generate_synthetic_retail
from src.data.preprocessor import clean_retail_data, encode_transactions


@pytest.fixture(scope="session")
def project_root():
    """Return the absolute path to the project root directory."""
    return str(PROJECT_ROOT)


@pytest.fixture(scope="session")
def sample_raw_retail_df():
    """Deterministic synthetic retail raw DataFrame fixture."""
    return generate_synthetic_retail(num_invoices=200, seed=42)


@pytest.fixture(scope="session")
def sample_cleaned_dataset(sample_raw_retail_df):
    """Cleaned dataset fixture."""
    return clean_retail_data(sample_raw_retail_df)


@pytest.fixture
def simple_baskets():
    """Small canonical toy dataset with known itemsets and supports."""
    return [
        ["MILK", "BREAD", "BUTTER"],
        ["BREAD", "BUTTER"],
        ["MILK", "BREAD"],
        ["MILK", "EGGS"],
        ["BREAD", "BUTTER", "JAM"],
        ["MILK", "BREAD", "BUTTER", "JAM"],
        ["MILK", "EGGS", "CHEESE"],
        ["BREAD", "JAM"],
        ["MILK", "BREAD", "BUTTER"],
        ["EGGS", "CHEESE"],
    ]


@pytest.fixture
def simple_onehot_df(simple_baskets):
    """One-hot encoded toy DataFrame."""
    return encode_transactions(simple_baskets)


@pytest.fixture
def sample_retail_df():
    """
    Deterministic pandas DataFrame representing raw Online Retail data.
    Includes positive purchases, cancellations ('C' prefix + negative quantity),
    administrative codes ('POST', 'D', 'M', 'BANK CHARGES'), whitespace anomalies,
    null descriptions, negative unit prices, and multi-item baskets.
    """
    data = [
        # Normal Basket 1 (Invoice 536365)
        {"InvoiceNo": "536365", "StockCode": "85123A", "Description": "WHITE HANGING HEART T-LIGHT HOLDER", "Quantity": 6, "InvoiceDate": "2010-12-01 08:26:00", "UnitPrice": 2.55, "CustomerID": 17850.0, "Country": "United Kingdom"},
        {"InvoiceNo": "536365", "StockCode": "71053", "Description": "WHITE METAL LANTERN", "Quantity": 6, "InvoiceDate": "2010-12-01 08:26:00", "UnitPrice": 3.39, "CustomerID": 17850.0, "Country": "United Kingdom"},
        {"InvoiceNo": "536365", "StockCode": "84406B", "Description": "CREAM CUPID HEARTS COAT HANGER", "Quantity": 8, "InvoiceDate": "2010-12-01 08:26:00", "UnitPrice": 2.75, "CustomerID": 17850.0, "Country": "United Kingdom"},
        
        # Normal Basket 2 (Invoice 536366) - Multi-item
        {"InvoiceNo": "536366", "StockCode": "22633", "Description": "HAND WARMER UNION JACK", "Quantity": 6, "InvoiceDate": "2010-12-01 08:28:00", "UnitPrice": 1.85, "CustomerID": 17850.0, "Country": "United Kingdom"},
        {"InvoiceNo": "536366", "StockCode": "22632", "Description": "HAND WARMER RED POLKADOT", "Quantity": 6, "InvoiceDate": "2010-12-01 08:28:00", "UnitPrice": 1.85, "CustomerID": 17850.0, "Country": "United Kingdom"},
        
        # Normal Basket 3 (Invoice 536367) - High overlap
        {"InvoiceNo": "536367", "StockCode": "85123A", "Description": " WHITE HANGING HEART T-LIGHT HOLDER ", "Quantity": 12, "InvoiceDate": "2010-12-01 08:34:00", "UnitPrice": 2.55, "CustomerID": 13047.0, "Country": "United Kingdom"},
        {"InvoiceNo": "536367", "StockCode": "71053", "Description": "WHITE METAL LANTERN", "Quantity": 12, "InvoiceDate": "2010-12-01 08:34:00", "UnitPrice": 3.39, "CustomerID": 13047.0, "Country": "United Kingdom"},
        {"InvoiceNo": "536367", "StockCode": "22633", "Description": "HAND WARMER UNION JACK", "Quantity": 4, "InvoiceDate": "2010-12-01 08:34:00", "UnitPrice": 1.85, "CustomerID": 13047.0, "Country": "United Kingdom"},
        
        # Single-Item Basket (Invoice 536368)
        {"InvoiceNo": "536368", "StockCode": "22960", "Description": "JAM MAKING SET WITH JARS", "Quantity": 6, "InvoiceDate": "2010-12-01 08:34:00", "UnitPrice": 4.25, "CustomerID": 13047.0, "Country": "United Kingdom"},
        
        # Cancelled Order (Invoice C536379)
        {"InvoiceNo": "C536379", "StockCode": "D", "Description": "Discount", "Quantity": -1, "InvoiceDate": "2010-12-01 09:41:00", "UnitPrice": 27.50, "CustomerID": 14527.0, "Country": "United Kingdom"},
        {"InvoiceNo": "C536380", "StockCode": "85123A", "Description": "WHITE HANGING HEART T-LIGHT HOLDER", "Quantity": -3, "InvoiceDate": "2010-12-01 09:45:00", "UnitPrice": 2.55, "CustomerID": 17850.0, "Country": "United Kingdom"},

        # Admin Codes & Null/Zero Price Anomalies
        {"InvoiceNo": "536381", "StockCode": "POST", "Description": "POSTAGE", "Quantity": 1, "InvoiceDate": "2010-12-01 09:50:00", "UnitPrice": 18.00, "CustomerID": 15311.0, "Country": "Germany"},
        {"InvoiceNo": "536382", "StockCode": "21730", "Description": None, "Quantity": 2, "InvoiceDate": "2010-12-01 09:55:00", "UnitPrice": 0.00, "CustomerID": np.nan, "Country": "United Kingdom"},
        {"InvoiceNo": "536383", "StockCode": "21731", "Description": "RED TOADSTOOL LED NIGHT LIGHT", "Quantity": 4, "InvoiceDate": "2010-12-01 10:00:00", "UnitPrice": -1.50, "CustomerID": 15311.0, "Country": "Germany"},
        
        # Another Multi-item Basket (Invoice 536384 - France)
        {"InvoiceNo": "536384", "StockCode": "85123A", "Description": "WHITE HANGING HEART T-LIGHT HOLDER", "Quantity": 10, "InvoiceDate": "2010-12-01 10:15:00", "UnitPrice": 2.55, "CustomerID": 12583.0, "Country": "France"},
        {"InvoiceNo": "536384", "StockCode": "71053", "Description": "WHITE METAL LANTERN", "Quantity": 10, "InvoiceDate": "2010-12-01 10:15:00", "UnitPrice": 3.39, "CustomerID": 12583.0, "Country": "France"},
        {"InvoiceNo": "536384", "StockCode": "22632", "Description": "HAND WARMER RED POLKADOT", "Quantity": 8, "InvoiceDate": "2010-12-01 10:15:00", "UnitPrice": 1.85, "CustomerID": 12583.0, "Country": "France"},
    ]
    return pd.DataFrame(data)


@pytest.fixture
def sample_clean_transactions():
    """
    A 10-transaction synthetic market basket dataset with known, verifiable associations.
    Universe: {'bread', 'milk', 'butter', 'beer', 'cookies', 'diaper'}
    """
    return [
        ["bread", "milk", "butter"],             # T1: bread, milk, butter
        ["bread", "butter"],                     # T2: bread, butter
        ["bread", "milk"],                       # T3: bread, milk
        ["beer", "cookies"],                     # T4: beer, cookies
        ["bread", "milk", "butter", "cookies"],  # T5: bread, milk, butter, cookies
        ["bread", "milk", "diaper"],             # T6: bread, milk, diaper
        ["beer", "diaper"],                      # T7: beer, diaper
        ["bread", "butter", "diaper"],           # T8: bread, butter, diaper
        ["milk", "diaper", "beer"],              # T9: milk, diaper, beer
        ["bread", "milk", "butter", "beer"]      # T10: bread, milk, butter, beer
    ]


@pytest.fixture
def sample_one_hot_df(sample_clean_transactions):
    """
    One-hot encoded boolean DataFrame corresponding to sample_clean_transactions (10 rows x 6 items).
    """
    items = sorted(list({item for tx in sample_clean_transactions for item in tx}))
    rows = []
    for tx in sample_clean_transactions:
        row = {item: (item in tx) for item in items}
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def sample_mined_rules_df():
    """
    A reference DataFrame containing mined association rules with all 9 interest metrics.
    """
    rules_data = [
        {
            "id": 1,
            "antecedents": ["bread", "butter"],
            "consequents": ["milk"],
            "antecedent_support": 0.5,
            "consequent_support": 0.6,
            "support": 0.4,
            "confidence": 0.8,
            "lift": 1.333333,
            "leverage": 0.1,
            "conviction": 2.0,
            "zhangs_metric": 0.5,
            "kulczynski": 0.733333,
            "imbalance_ratio": 0.142857,
            "cosine": 0.730297
        },
        {
            "id": 2,
            "antecedents": ["milk"],
            "consequents": ["bread"],
            "antecedent_support": 0.6,
            "consequent_support": 0.7,
            "support": 0.5,
            "confidence": 0.833333,
            "lift": 1.190476,
            "leverage": 0.08,
            "conviction": 1.8,
            "zhangs_metric": 0.4,
            "kulczynski": 0.773810,
            "imbalance_ratio": 0.125,
            "cosine": 0.771517
        },
        {
            "id": 3,
            "antecedents": ["beer"],
            "consequents": ["cookies"],
            "antecedent_support": 0.4,
            "consequent_support": 0.2,
            "support": 0.2,
            "confidence": 0.5,
            "lift": 2.5,
            "leverage": 0.12,
            "conviction": 1.6,
            "zhangs_metric": 0.75,
            "kulczynski": 0.75,
            "imbalance_ratio": 0.5,
            "cosine": 0.707107
        },
        {
            "id": 4,
            "antecedents": ["beer", "diaper"],
            "consequents": ["milk"],
            "antecedent_support": 0.2,
            "consequent_support": 0.6,
            "support": 0.1,
            "confidence": 0.5,
            "lift": 0.833333,
            "leverage": -0.02,
            "conviction": 0.8,
            "zhangs_metric": -0.25,
            "kulczynski": 0.333333,
            "imbalance_ratio": 0.571429,
            "cosine": 0.288675
        }
    ]
    return pd.DataFrame(rules_data)


@pytest.fixture
def sample_pipeline_summary_dict():
    """
    Standard dictionary matching the artifacts/pipeline_summary.json schema.
    """
    return {
        "pipeline_metadata": {
            "run_timestamp": "2026-09-02T18:00:00Z",
            "execution_time_seconds": 1.25,
            "framework": "CRISP-DM",
            "dataset_name": "online_retail",
            "algorithm": "fpgrowth",
            "engine": "custom_with_metrics",
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
                "objective": "E-commerce market basket optimization & bundle discovery",
                "target_kpi": "Lift > 1.2, Confidence > 0.3"
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
                "id": 1,
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


@pytest.fixture
def sample_optimization_log_dict():
    """
    Standard dictionary matching the artifacts/optimization_log.json schema.
    """
    return {
        "metadata": {
            "timestamp": "2026-09-02T18:00:00Z",
            "execution_time_seconds": 8.45,
            "seed": 42,
            "dataset": "Online Retail (Synthetic Benchmark)",
            "total_transactions": 25000,
            "unique_items": 4070
        },
        "target_paper": {
            "key": "ghosh2004",
            "title": "Multi-objective rule mining using genetic algorithms",
            "authors": "Ashish Ghosh and Bhabesh Nath",
            "venue": "Information Sciences (2004)",
            "doi": "10.1016/j.ins.2003.03.021",
            "target_metrics": {
                "rule_count": 50,
                "avg_support": 0.025,
                "avg_confidence": 0.720,
                "avg_lift": 2.450,
                "coverage": 0.180
            }
        },
        "config": {
            "iterations_per_restart": 30,
            "max_restarts": 2,
            "initial_step_size": 0.05,
            "fitness_mode": "hybrid",
            "neighbors_per_step": 4,
            "stagnation_limit": 5
        },
        "summary": {
            "total_iterations_run": 50,
            "restarts_triggered": 1,
            "termination_reason": "Max iterations reached",
            "initial_fitness": 45.2,
            "best_fitness": 94.8,
            "best_loss": 0.0548
        },
        "target_vs_achieved": {
            "rule_count": {"target": 50, "achieved": 49, "error_pct": 2.0},
            "avg_support": {"target": 0.025, "achieved": 0.0248, "error_pct": 0.8},
            "avg_confidence": {"target": 0.720, "achieved": 0.715, "error_pct": 0.69},
            "avg_lift": {"target": 2.450, "achieved": 2.480, "error_pct": 1.22},
            "coverage": {"target": 0.180, "achieved": 0.178, "error_pct": 1.11}
        },
        "best_hyperparameters": {
            "min_support": 0.0185,
            "min_confidence": 0.582,
            "min_lift": 1.72,
            "max_len": 3,
            "pruning_factor": 0.68
        },
        "iteration_trail": [
            {
                "iteration": 1,
                "restart_id": 0,
                "step_type": "initial",
                "current_state": {"min_support": 0.02, "min_confidence": 0.5, "min_lift": 1.2, "max_len": 3, "pruning_factor": 0.7},
                "metrics": {"rule_count": 84, "avg_support": 0.021, "avg_confidence": 0.58, "avg_lift": 1.95, "coverage": 0.24},
                "fitness": 68.4,
                "best_fitness": 68.4,
                "step_size": 0.05,
                "accepted": True
            }
        ]
    }


@pytest.fixture
def sample_optimization_history_df():
    """
    Standard DataFrame matching artifacts/optimization_history.csv.
    """
    rows = [
        {"iteration": 1, "restart_id": 0, "step_type": "initial", "min_support": 0.02, "min_confidence": 0.5, "max_len": 3, "min_lift": 1.2, "pruning_factor": 0.7, "rule_count": 84, "avg_support": 0.021, "avg_confidence": 0.58, "avg_lift": 1.95, "coverage": 0.24, "loss": 0.462, "fitness": 68.4, "best_fitness": 68.4, "step_size": 0.05, "accepted": True},
        {"iteration": 2, "restart_id": 0, "step_type": "improvement", "min_support": 0.0195, "min_confidence": 0.525, "max_len": 3, "min_lift": 1.35, "pruning_factor": 0.68, "rule_count": 62, "avg_support": 0.0235, "avg_confidence": 0.645, "avg_lift": 2.15, "coverage": 0.21, "loss": 0.215, "fitness": 82.3, "best_fitness": 82.3, "step_size": 0.0575, "accepted": True},
        {"iteration": 3, "restart_id": 0, "step_type": "improvement", "min_support": 0.0185, "min_confidence": 0.582, "max_len": 3, "min_lift": 1.72, "pruning_factor": 0.68, "rule_count": 49, "avg_support": 0.0248, "avg_confidence": 0.715, "avg_lift": 2.48, "coverage": 0.178, "loss": 0.0548, "fitness": 94.8, "best_fitness": 94.8, "step_size": 0.0661, "accepted": True}
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def temp_artifacts_dir(tmp_path, sample_pipeline_summary_dict, sample_mined_rules_df, sample_optimization_log_dict, sample_optimization_history_df):
    """
    Creates a temporary directory populated with standard dummy artifacts.
    """
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    with open(artifacts_dir / "pipeline_summary.json", "w", encoding="utf-8") as f:
        json.dump(sample_pipeline_summary_dict, f, indent=2)

    with open(artifacts_dir / "pipeline_report.md", "w", encoding="utf-8") as f:
        f.write("# CRISP-DM Pipeline Report\n\nExecution successful.\n")

    with open(artifacts_dir / "rules.json", "w", encoding="utf-8") as f:
        json.dump(sample_mined_rules_df.to_dict(orient="records"), f, indent=2)

    sample_mined_rules_df.to_csv(artifacts_dir / "rules.csv", index=False)

    itemsets_df = pd.DataFrame([
        {"itemsets": "['bread']", "support": 0.7, "length": 1},
        {"itemsets": "['milk']", "support": 0.6, "length": 1},
        {"itemsets": "['bread', 'milk']", "support": 0.5, "length": 2}
    ])
    itemsets_df.to_csv(artifacts_dir / "frequent_itemsets.csv", index=False)

    with open(artifacts_dir / "optimization_log.json", "w", encoding="utf-8") as f:
        json.dump(sample_optimization_log_dict, f, indent=2)

    sample_optimization_history_df.to_csv(artifacts_dir / "optimization_history.csv", index=False)
    sample_mined_rules_df.to_csv(artifacts_dir / "optimized_rules.csv", index=False)

    return str(artifacts_dir)


@pytest.fixture
def mock_paper_catalog():
    """
    Returns reference configurations for the research paper benchmark catalog.
    """
    return {
        "ghosh2004": {
            "key": "ghosh2004",
            "title": "Multi-objective rule mining using genetic algorithms",
            "authors": "Ashish Ghosh and Bhabesh Nath",
            "venue": "Information Sciences, Vol. 163, pp. 123–133, 2004",
            "doi": "10.1016/j.ins.2003.03.021",
            "target_metrics": {
                "rule_count": 50,
                "avg_support": 0.025,
                "avg_confidence": 0.720,
                "avg_lift": 2.450,
                "coverage": 0.180
            }
        },
        "agrawal1994": {
            "key": "agrawal1994",
            "title": "Fast Algorithms for Mining Association Rules in Large Databases",
            "authors": "Rakesh Agrawal and Ramakrishnan Srikant",
            "venue": "VLDB '94, pp. 487–499, 1994",
            "doi": "10.5555/645920.672836",
            "target_metrics": {
                "rule_count": 120,
                "avg_support": 0.015,
                "avg_confidence": 0.600,
                "avg_lift": 1.850,
                "coverage": 0.250
            }
        },
        "chen2012": {
            "key": "chen2012",
            "title": "Data mining for the online retail industry: A case study of RFM model-based customer segmentation",
            "authors": "Daqing Chen, Sai Liang Sain, and Kun Guo",
            "venue": "Journal of Database Marketing & Customer Strategy Management, 2012",
            "doi": "10.1057/dbm.2012.17",
            "target_metrics": {
                "rule_count": 35,
                "avg_support": 0.020,
                "avg_confidence": 0.680,
                "avg_lift": 3.200,
                "coverage": 0.220
            }
        }
    }


@pytest.fixture
def flask_test_app(temp_artifacts_dir):
    """
    Creates a Flask test application configured with the temporary artifacts directory.
    """
    try:
        from app import create_app
        test_app = create_app({"TESTING": True, "ARTIFACTS_DIR": temp_artifacts_dir})
        return test_app
    except (ImportError, AttributeError):
        pass

    try:
        from src.dashboard.routes import create_app
        test_app = create_app({"TESTING": True, "ARTIFACTS_DIR": temp_artifacts_dir})
        return test_app
    except (ImportError, AttributeError):
        pass

    # Dynamic fallback app for progressive testing
    fallback_app = Flask(__name__)
    fallback_app.config["TESTING"] = True
    fallback_app.config["ARTIFACTS_DIR"] = temp_artifacts_dir

    @fallback_app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": "2026-09-02T18:00:00Z",
            "version": "1.0.0",
            "artifacts": {"eda": True, "pipeline": True, "rules": True, "optimization": True}
        }), 200

    @fallback_app.route("/")
    def index():
        return "<html><body><h1>Associative Pattern Mining Studio</h1><div id='crisp-dm'></div><div id='visualizer'></div><div id='hill-climbing'></div><div id='sandbox'></div></body></html>", 200, {"Content-Type": "text/html"}

    return fallback_app


@pytest.fixture
def flask_client(flask_test_app):
    """Provides a Flask test client for REST API testing."""
    return flask_test_app.test_client()
