#!/usr/bin/env python3
"""
CLI Entrypoint for CRISP-DM Associative Pattern Mining Pipeline (Requirement 1).

Executes end-to-end CRISP-DM stages:
1. Business Understanding
2. Data Understanding (EDA)
3. Data Preparation
4. Modeling (Apriori / FP-Growth)
5. Evaluation (Multi-Metric Filtering & Redundancy Pruning)
6. Deployment (Summary, Rules, Reports Artifact Generation)
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DEFAULT_ALGORITHM,
    DEFAULT_COUNTRY,
    DEFAULT_ENGINE,
    DEFAULT_MAX_LEN,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_METRIC_VAL,
    DEFAULT_MIN_SUPPORT,
    DEFAULT_PRIMARY_METRIC,
)
from src.deployment.pipeline import CRISPDMPipeline
from src.utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the CRISP-DM pipeline runner."""
    parser = argparse.ArgumentParser(
        description="CRISP-DM Associative Pattern Mining Engine CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="online_retail",
        help="Dataset name ('online_retail', 'groceries', 'bakery', 'synthetic') or path to custom CSV file.",
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default=DEFAULT_ALGORITHM,
        choices=["fpgrowth", "apriori"],
        help="Frequent pattern mining algorithm.",
    )
    parser.add_argument(
        "--min-support",
        type=float,
        default=DEFAULT_MIN_SUPPORT,
        help="Minimum support threshold (0.001 - 1.0).",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Minimum confidence threshold (0.0 - 1.0).",
    )
    parser.add_argument(
        "--metric",
        type=str,
        default=DEFAULT_PRIMARY_METRIC,
        choices=["lift", "confidence", "support", "zhangs_metric", "kulczynski", "cosine", "leverage"],
        help="Primary metric used for threshold filtering.",
    )
    parser.add_argument(
        "--min-metric-val",
        type=float,
        default=DEFAULT_MIN_METRIC_VAL,
        help="Minimum threshold value for the primary metric.",
    )
    parser.add_argument(
        "--max-len",
        type=int,
        default=DEFAULT_MAX_LEN,
        help="Maximum itemset length to discover.",
    )
    parser.add_argument(
        "--country",
        type=str,
        default=DEFAULT_COUNTRY,
        help="Filter transactions by country (e.g., 'United Kingdom', 'France', 'all').",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts",
        help="Directory path to save deployment artifacts.",
    )
    parser.add_argument(
        "--generate-synthetic",
        action="store_true",
        help="Force generation of synthetic dataset even if dataset exists.",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default=DEFAULT_ENGINE,
        choices=["auto", "mlxtend", "custom"],
        help="Execution engine for pattern mining algorithms.",
    )
    parser.add_argument(
        "--prune-redundant",
        dest="prune_redundant",
        action="store_true",
        default=True,
        help="Prune redundant sub-rules with equal or lower confidence.",
    )
    parser.add_argument(
        "--no-prune-redundant",
        dest="prune_redundant",
        action="store_false",
        help="Disable redundancy pruning.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all logging except warnings and errors.",
    )

    return parser.parse_args()


def main() -> int:
    """Execute the pipeline from CLI and return status code."""
    args = parse_args()
    logger = setup_logger(verbose=args.verbose, quiet=args.quiet)

    try:
        pipeline = CRISPDMPipeline(
            dataset_name=args.dataset,
            algorithm=args.algorithm,
            min_support=args.min_support,
            min_confidence=args.min_confidence,
            metric=args.metric,
            min_metric_val=args.min_metric_val,
            max_len=args.max_len,
            country=args.country,
            engine=args.engine,
            prune_redundant=args.prune_redundant,
            output_dir=args.output_dir,
            force_synthetic=args.generate_synthetic,
        )

        result = pipeline.run()

        # Print brief CLI summary table
        print("\n" + "=" * 70)
        print("  CRISP-DM PIPELINE SUMMARY")
        print("=" * 70)
        print(f"  • Dataset: {result.summary_dict['pipeline_metadata']['dataset_name']}")
        print(f"  • Algorithm: {result.summary_dict['pipeline_metadata']['algorithm']}")
        print(f"  • Cleaned Baskets: {result.cleaned_data.unique_invoices:,}")
        print(f"  • Unique Items: {result.cleaned_data.unique_items:,}")
        print(f"  • Discovered Frequent Itemsets: {len(result.itemsets_df):,}")
        print(f"  • Discovered Actionable Rules: {len(result.rules_df):,}")
        print(f"  • Execution Time: {result.execution_time_seconds:.2f}s")
        print(f"  • Artifacts Directory: {result.output_dir.resolve()}")
        print("=" * 70 + "\n")

        return 0

    except Exception as e:
        logger.error(f"CRISP-DM Pipeline execution failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
