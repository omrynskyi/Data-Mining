"""
Artifact Exporter for CRISP-DM Associative Pattern Mining.
Generates JSON, CSV, and human-readable Markdown summary reports.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from config import ARTIFACTS_DIR
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.exporter")


class CustomJSONEncoder(json.JSONEncoder):
    """JSON Encoder that handles NumPy types, sets, NaN, and infinity values."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (np.ndarray, set, frozenset)):
            return list(obj)
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)


def sanitize_value(val: Any) -> Any:
    """Sanitize float / numpy values for JSON compliance."""
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(float(val), 6)
    if isinstance(val, (set, frozenset, list, tuple)):
        return [sanitize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
    return val


def export_pipeline_summary(
    summary_dict: Dict[str, Any],
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Export CRISP-DM summary dictionary to JSON."""
    out_file = Path(output_path) if output_path else ARTIFACTS_DIR / "pipeline_summary.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_value(summary_dict)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(sanitized, f, cls=CustomJSONEncoder, indent=2, ensure_ascii=False)

    logger.info(f"Exported pipeline summary to: {out_file}")
    return out_file


def export_rules(
    rules_df: pd.DataFrame,
    csv_path: Optional[Union[str, Path]] = None,
    json_path: Optional[Union[str, Path]] = None,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Export mined association rules to CSV and JSON."""
    out_csv = Path(csv_path) if csv_path else ARTIFACTS_DIR / "rules.csv"
    out_json = Path(json_path) if json_path else ARTIFACTS_DIR / "rules.json"

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Export CSV
    csv_df = rules_df.copy()
    if not csv_df.empty:
        csv_df["antecedents"] = csv_df["antecedents"].apply(lambda x: ", ".join(x) if isinstance(x, (list, set, frozenset)) else str(x))
        csv_df["consequents"] = csv_df["consequents"].apply(lambda x: ", ".join(x) if isinstance(x, (list, set, frozenset)) else str(x))
    csv_df.to_csv(out_csv, index=False)
    logger.info(f"Exported {len(rules_df)} rules to CSV: {out_csv}")

    # Export JSON
    rules_list: List[Dict[str, Any]] = []
    for _, row in rules_df.iterrows():
        ant = list(row["antecedents"]) if isinstance(row["antecedents"], (list, set, frozenset)) else [str(row["antecedents"])]
        con = list(row["consequents"]) if isinstance(row["consequents"], (list, set, frozenset)) else [str(row["consequents"])]
        rule_obj = {
            "id": int(row.get("id", 0)),
            "antecedents": ant,
            "consequents": con,
            "support": float(row.get("support", 0.0)),
            "confidence": float(row.get("confidence", 0.0)),
            "lift": float(row.get("lift", 0.0)),
            "leverage": float(row.get("leverage", 0.0)),
            "conviction": float(row.get("conviction", 0.0)),
            "zhangs_metric": float(row.get("zhangs_metric", 0.0)),
            "kulczynski": float(row.get("kulczynski", 0.0)),
            "imbalance_ratio": float(row.get("imbalance_ratio", 0.0)),
            "cosine": float(row.get("cosine", 0.0)),
        }
        if "rule_category" in row:
            rule_obj["rule_category"] = str(row["rule_category"])
        if "composite_score" in row and not pd.isna(row["composite_score"]):
            rule_obj["composite_score"] = float(row["composite_score"])
        rules_list.append(sanitize_value(rule_obj))

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rules_list, f, cls=CustomJSONEncoder, indent=2, ensure_ascii=False)
    logger.info(f"Exported {len(rules_list)} rules to JSON: {out_json}")

    return out_csv, out_json


def export_frequent_itemsets(
    itemsets_df: pd.DataFrame,
    csv_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Export frequent itemsets to CSV."""
    out_csv = Path(csv_path) if csv_path else ARTIFACTS_DIR / "frequent_itemsets.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    df = itemsets_df.copy()
    if not df.empty and "itemsets" in df.columns:
        df["itemsets"] = df["itemsets"].apply(lambda x: ", ".join(sorted(list(x))) if isinstance(x, (set, frozenset, list)) else str(x))
    df.to_csv(out_csv, index=False)
    logger.info(f"Exported {len(itemsets_df)} frequent itemsets to CSV: {out_csv}")
    return out_csv


def export_markdown_report(
    summary_dict: Dict[str, Any],
    rules_df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Generate comprehensive human-readable Markdown report of CRISP-DM execution."""
    out_file = Path(output_path) if output_path else ARTIFACTS_DIR / "pipeline_report.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    meta = summary_dict.get("pipeline_metadata", {})
    stages = summary_dict.get("crisp_dm_stages", {})
    biz = stages.get("business_understanding", {})
    eda = stages.get("data_understanding", {})
    prep = stages.get("data_preparation", {})
    model = stages.get("modeling", {})
    eval_stage = stages.get("evaluation", {})

    top_rules = rules_df.head(10)

    lines = [
        "# CRISP-DM Pipeline Report: Associative Pattern Mining",
        "",
        f"**Run Timestamp**: `{meta.get('run_timestamp', 'N/A')}`  ",
        f"**Execution Duration**: `{meta.get('execution_time_seconds', 0.0):.2f}s`  ",
        f"**Dataset**: `{meta.get('dataset_name', 'N/A')}`  ",
        f"**Algorithm**: `{meta.get('algorithm', 'N/A')}` (`{meta.get('engine', 'auto')}`)  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"An end-to-end CRISP-DM data mining pipeline was executed on **{meta.get('dataset_name')}**.",
        f"The pipeline cleaned `{prep.get('cleaned_transactions_count', prep.get('unique_invoices', 0)):,}` transactions across `{prep.get('cleaned_unique_items_count', prep.get('unique_items', 0)):,}` products, discovering **{model.get('frequent_itemsets_total', 0):,}** frequent itemsets and **{eval_stage.get('final_actionable_rules_count', 0):,}** high-value association rules after redundancy pruning.",
        "",
        "---",
        "",
        "## Phase 1: Business Understanding",
        f"- **Primary Objective**: {biz.get('objective', 'Cross-sell optimization and basket analysis')}",
        f"- **Success Criteria / Target KPI**: {biz.get('target_kpi', 'Lift > 1.2, Confidence > 0.3')}",
        "",
        "## Phase 2: Data Understanding (EDA)",
        f"- **Raw Transactions**: `{eda.get('raw_records_count', 0):,}` line items across `{eda.get('unique_invoices', 0):,}` unique baskets",
        f"- **Catalog Size**: `{eda.get('unique_items', 0):,}` unique products",
        f"- **Matrix Sparsity**: `{eda.get('sparsity_pct', 0.0):.2f}%` (Density: `{eda.get('matrix_density_pct', 0.0):.2f}%`)",
        f"- **Cancellations / Returns**: `{eda.get('cancellation_rate_pct', 0.0):.2f}%`",
        "",
        "### Basket Size Distribution",
        "| Statistic | Value |",
        "| :--- | :--- |",
    ]

    bstats = eda.get("basket_size_stats", {})
    for k, v in bstats.items():
        lines.append(f"| `{k}` | `{v}` |")

    lines.extend([
        "",
        "## Phase 3: Data Preparation",
        f"- **Cleaning Pipeline Steps Applied**:",
    ])
    for step in prep.get("cleaning_steps_applied", []):
        lines.append(f"  - `{step}`")

    lines.extend([
        f"- **Cleaned Baskets**: `{prep.get('cleaned_transactions_count', prep.get('unique_invoices', 0)):,}`",
        f"- **One-Hot Matrix Shape**: `{prep.get('matrix_shape', [0, 0])}`",
        "",
        "## Phase 4: Modeling (Frequent Itemsets & Rule Mining)",
        f"- **Algorithm**: `{meta.get('algorithm')}` with `min_support={meta.get('parameters', {}).get('min_support')}`",
        f"- **Frequent Itemsets Found**: `{model.get('frequent_itemsets_total', 0):,}`",
        f"- **Raw Association Rules Extracted**: `{model.get('raw_rules_generated', 0):,}`",
        "",
        "## Phase 5: Evaluation & Redundancy Pruning",
        f"- **Rules after Threshold Filtering**: `{eval_stage.get('rules_after_threshold_filtering', 0):,}`",
        f"- **Redundant Sub-Rules Pruned**: `{eval_stage.get('redundant_rules_pruned', 0):,}`",
        f"- **Final Actionable Rules**: `{eval_stage.get('final_actionable_rules_count', 0):,}`",
        "",
        "### Rule Business Categories Breakdown",
    ])

    cats = eval_stage.get("rule_categories", {})
    for cat_name, cat_count in cats.items():
        lines.append(f"- **{cat_name}**: `{cat_count}`")

    lines.extend([
        "",
        "---",
        "",
        "## Top 10 Discovered Association Rules",
        "",
        "| # | Antecedent | Consequent | Supp | Conf | Lift | Lev | Conv | Zhang | Kulc | IR | Cos | Cat |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])

    for _, row in top_rules.iterrows():
        ant_str = ", ".join(row["antecedents"]) if isinstance(row["antecedents"], (list, set, frozenset)) else str(row["antecedents"])
        con_str = ", ".join(row["consequents"]) if isinstance(row["consequents"], (list, set, frozenset)) else str(row["consequents"])
        lines.append(
            f"| {row.get('id', 0)} | `{ant_str}` | `{con_str}` | "
            f"{row.get('support', 0):.3f} | {row.get('confidence', 0):.3f} | {row.get('lift', 0):.2f} | "
            f"{row.get('leverage', 0):.3f} | {row.get('conviction', 0):.2f} | {row.get('zhangs_metric', 0):.2f} | "
            f"{row.get('kulczynski', 0):.2f} | {row.get('imbalance_ratio', 0):.2f} | {row.get('cosine', 0):.2f} | "
            f"{row.get('rule_category', 'N/A')} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Phase 6: Deployment Artifacts",
        "- `artifacts/pipeline_summary.json` (Machine-readable full CRISP-DM metadata)",
        "- `artifacts/pipeline_report.md` (This executive summary report)",
        "- `artifacts/rules.csv` (Mined association rules in tabular format)",
        "- `artifacts/rules.json` (Mined association rules in JSON format for dashboard & API consumption)",
        "- `artifacts/frequent_itemsets.csv` (All frequent itemsets with support and lengths)",
        "",
    ])

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Exported human-readable markdown report to: {out_file}")
    return out_file
