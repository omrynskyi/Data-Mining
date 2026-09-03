#!/usr/bin/env python3
"""
CLI Runner for the Autoresearch Benchmark-Alignment Engine (R3).

Loads the Mall Customer dataset, runs a steepest-ascent hill-climbing search over
the clustering configuration space against a cited academic benchmark, and emits:
  - optimization_log.md                       (paper citation, baselines, iteration log)
  - artifacts/autoresearch_output.json        (+ dashboard/public/data copy)
  - artifacts/models/best_autoresearch_model.joblib
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import joblib

from src.autoresearch import (
    BENCHMARK_PAPER,
    HillClimbingOptimizer,
    SearchState,
    render_optimization_log,
)
from src.config import (
    ARTIFACTS_DIR,
    DASHBOARD_DATA_DIR,
    DEFAULT_RANDOM_STATE,
    DEFAULT_RAW_DATA_PATH,
    PROJECT_ROOT,
)
from src.data_loader import DataLoader
from src.export import sanitize_json

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_autoresearch")


def parse_args(args_list: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for the autoresearch optimizer."""
    parser = argparse.ArgumentParser(
        description="Autoresearch: hill-climbing alignment of the clustering pipeline "
                    "with a benchmark academic paper."
    )
    parser.add_argument(
        "--data",
        "--data-path",
        type=str,
        default=str(DEFAULT_RAW_DATA_PATH),
        help=f"Path to input CSV dataset (default: {DEFAULT_RAW_DATA_PATH})",
    )
    parser.add_argument(
        "--iterations",
        "--max-iterations",
        type=int,
        default=12,
        help="Maximum number of hill-climbing iterations (default: 12)",
    )
    parser.add_argument(
        "--step-size",
        type=float,
        default=0.05,
        help="Continuous mutation step used for DBSCAN eps moves (default: 0.05)",
    )
    parser.add_argument(
        "--output",
        "--log",
        type=str,
        default=str(PROJECT_ROOT / "optimization_log.md"),
        help="Path of the generated markdown optimization log (default: optimization_log.md)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(ARTIFACTS_DIR),
        help=f"Directory for JSON and model artifacts (default: {ARTIFACTS_DIR})",
    )
    parser.add_argument(
        "--dashboard-dir",
        type=str,
        default=str(DASHBOARD_DATA_DIR),
        help=f"Directory for dashboard public JSON data (default: {DASHBOARD_DATA_DIR})",
    )
    parser.add_argument(
        "--start-algorithm",
        type=str,
        choices=["kmeans", "agglomerative", "dbscan", "gmm"],
        default="kmeans",
        help="Algorithm of the baseline (iteration 0) configuration (default: kmeans)",
    )
    parser.add_argument(
        "--start-k",
        type=int,
        default=3,
        help="Cluster count of the baseline (iteration 0) configuration (default: 3)",
    )
    parser.add_argument(
        "--start-features",
        type=str,
        choices=["2d", "3d", "4d"],
        default="2d",
        help="Feature space of the baseline configuration (default: 2d)",
    )
    parser.add_argument(
        "--start-scaler",
        type=str,
        choices=["none", "standard", "minmax", "robust"],
        default="none",
        help="Scaler of the baseline configuration (default: none)",
    )
    parser.add_argument(
        "--random-state",
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_STATE,
        help=f"Random seed for reproducibility (default: {DEFAULT_RANDOM_STATE})",
    )
    parser.add_argument(
        "--no-export-dashboard",
        dest="export_dashboard",
        action="store_false",
        default=True,
        help="Disable copying autoresearch_output.json into the dashboard directory",
    )
    parser.add_argument("-q", "--quiet", action="store_true", default=False, help="Reduce log output")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Enable debug logging")

    return parser.parse_args(args_list)


def build_initial_state(args: argparse.Namespace) -> SearchState:
    """Constructs the iteration-0 baseline configuration from CLI arguments."""
    if args.start_algorithm == "dbscan":
        params: Dict[str, Any] = {"eps": 0.4, "min_samples": 5}
    elif args.start_algorithm == "agglomerative":
        params = {"k": args.start_k, "linkage": "ward"}
    elif args.start_algorithm == "gmm":
        params = {"k": args.start_k, "covariance_type": "full"}
    else:
        params = {"k": args.start_k}

    return SearchState(
        features=args.start_features,
        scaler=args.start_scaler,
        algorithm=args.start_algorithm,
        params=params,
    )


def run(args: argparse.Namespace) -> int:
    """Executes the autoresearch optimization and writes all artifacts."""
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("autoresearch").setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.WARNING)
        logging.getLogger("autoresearch").setLevel(logging.WARNING)

    if args.iterations < 1:
        logger.error(f"--iterations must be >= 1, got {args.iterations}")
        return 1
    if args.step_size <= 0:
        logger.error(f"--step-size must be positive, got {args.step_size}")
        return 1
    if not (2 <= args.start_k <= 10):
        logger.error(f"--start-k must be within [2, 10], got {args.start_k}")
        return 1

    try:
        if not args.quiet:
            logger.info("=" * 80)
            logger.info("        AUTORESEARCH: BENCHMARK ALIGNMENT VIA HILL CLIMBING")
            logger.info("=" * 80)
            logger.info(f"Benchmark paper: {BENCHMARK_PAPER['title']} ({BENCHMARK_PAPER['year']})")

        logger.info(f"[1/4] Loading dataset from {args.data}")
        df = DataLoader(data_path=args.data).load_raw_data()
        logger.info(f"      Loaded {len(df)} validated customer records.")

        logger.info(
            f"[2/4] Running hill-climbing search (max {args.iterations} iterations, "
            f"step size {args.step_size})..."
        )
        optimizer = HillClimbingOptimizer(
            df=df,
            max_iterations=args.iterations,
            step_size=args.step_size,
            random_state=args.random_state,
            initial_state=build_initial_state(args),
        )
        payload = optimizer.run()

        logger.info("[3/4] Exporting autoresearch JSON artifacts and best model...")
        artifacts_dir = Path(args.output_dir)
        models_dir = artifacts_dir / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        clean_payload = sanitize_json(payload)
        json_path = artifacts_dir / "autoresearch_output.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        logger.info(f"      Wrote {json_path}")

        if args.export_dashboard and args.dashboard_dir:
            try:
                dash_dir = Path(args.dashboard_dir)
                dash_dir.mkdir(parents=True, exist_ok=True)
                dash_file = dash_dir / "autoresearch_output.json"
                with open(dash_file, "w", encoding="utf-8") as f:
                    json.dump(clean_payload, f, indent=2)
                logger.info(f"      Synchronized dashboard data to {dash_file}")
            except Exception as exc:
                logger.warning(f"      Could not sync autoresearch data to dashboard ({exc}).")

        best_model = optimizer.best_record.get("model") if optimizer.best_record else None
        if best_model is not None:
            model_path = models_dir / "best_autoresearch_model.joblib"
            joblib.dump(
                {
                    "model": best_model,
                    "preprocessor": optimizer.best_record.get("preprocessor"),
                    "configuration": payload["best_configuration"],
                    "metrics": payload["optimized_metrics"],
                },
                model_path,
            )
            logger.info(f"      Serialized best model bundle to {model_path}")

        logger.info("[4/4] Rendering optimization_log.md...")
        log_path = Path(args.output)
        if not log_path.is_absolute():
            log_path = PROJECT_ROOT / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(render_optimization_log(payload), encoding="utf-8")
        logger.info(f"      Wrote {log_path}")

        if not args.quiet:
            opt = payload["optimized_metrics"]
            align = payload["benchmark_alignment"]
            logger.info("=" * 80)
            logger.info(
                f"[SUCCESS] Baseline silhouette {payload['baseline_metrics']['silhouette_score']} "
                f"-> optimized {opt['silhouette_score']} "
                f"({payload['improvement_summary']['percentage_improvement']:+.2f}%)"
            )
            logger.info(
                f"[SUCCESS] Best config: {opt['algorithm']} | {opt['feature_space']} | "
                f"scaler={opt['scaler']} | {opt['hyperparameters']}"
            )
            logger.info(
                f"[SUCCESS] Paper target {align['paper_silhouette_target']} "
                f"reached: {align['paper_target_reached']} "
                f"({align['relative_to_paper_pct']}% of published score)"
            )
            logger.info("=" * 80)

        return 0

    except FileNotFoundError as fnf_err:
        logger.error(f"File error: {fnf_err}")
        return 1
    except Exception as exc:
        logger.error(f"Autoresearch execution failed: {exc}", exc_info=args.verbose)
        return 1


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
