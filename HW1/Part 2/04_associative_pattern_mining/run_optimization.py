#!/usr/bin/env python3
"""
CLI Entrypoint for Automated Research & Hill Climbing Optimization (Requirement 2).

Selects a published associative pattern mining study, then searches the 5D mining
hyperparameter space -- (min_support, min_confidence, min_lift, max_len,
pruning_factor) -- for the configuration whose discovered rule set best
reproduces that paper's reported operating point on our own corpus.

Examples
--------
    python run_optimization.py
    python run_optimization.py --target-paper chen2012 --iterations 40 --restarts 3
    python run_optimization.py --list-papers
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import ARTIFACTS_DIR
from src.data.loader import load_dataset
from src.data.preprocessor import clean_retail_data
from src.optimization.hill_climber import HillClimber
from src.optimization.logger import export_all
from src.optimization.papers import PAPER_CATALOG, get_paper_profile, list_available_papers
from src.utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the hill climbing optimizer."""
    parser = argparse.ArgumentParser(
        description="Automated Research Paper Matching via Hill Climbing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--target-paper",
        type=str,
        default="ghosh2004",
        help=(
            "Research paper to match: a catalog key "
            f"({', '.join(list_available_papers())}) or a path to a custom profile JSON."
        ),
    )
    parser.add_argument(
        "--list-papers",
        action="store_true",
        help="Print the research paper benchmark catalog and exit.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="synthetic",
        help="Dataset name ('online_retail', 'groceries', 'bakery', 'synthetic') or path to a CSV.",
    )
    parser.add_argument(
        "--country",
        type=str,
        default="all",
        help="Restrict the corpus to a single country before mining.",
    )
    parser.add_argument(
        "--fitness-mode",
        type=str,
        default="hybrid",
        choices=["paper_match", "composite", "hybrid"],
        help="Fitness formulation driving the search.",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.70,
        help="Share of hybrid fitness attributed to paper matching (0-1).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="Hill climbing iterations per restart segment.",
    )
    parser.add_argument(
        "--restarts",
        type=int,
        default=3,
        help="Number of search segments; 1 means a single climb with no restart.",
    )
    parser.add_argument(
        "--neighbors",
        type=int,
        default=12,
        help="Neighbours sampled and evaluated per steepest-ascent step.",
    )
    parser.add_argument(
        "--scout",
        type=int,
        default=768,
        help=(
            "Latin Hypercube points swept before climbing to pick each segment's "
            "starting basin. Set 0 to climb from the domain default instead."
        ),
    )
    parser.add_argument(
        "--step-size",
        type=float,
        default=0.05,
        help="Initial mutation radius, as a fraction of each dimension's span.",
    )
    parser.add_argument(
        "--stagnation-limit",
        type=int,
        default=5,
        help="Iterations without improvement before a restart or step-size kick.",
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="fpgrowth",
        choices=["fpgrowth", "apriori"],
        help="Frequent itemset algorithm used to build the candidate rule superset.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument(
        "--output-log",
        type=str,
        default=str(ARTIFACTS_DIR / "optimization_log.json"),
        help="Destination for the JSON audit log.",
    )
    parser.add_argument(
        "--output-history",
        type=str,
        default=str(ARTIFACTS_DIR / "optimization_history.csv"),
        help="Destination for the iteration-by-iteration history CSV.",
    )
    parser.add_argument(
        "--output-rules",
        type=str,
        default=str(ARTIFACTS_DIR / "optimized_rules.csv"),
        help="Destination for the champion configuration's rule set.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Re-mine the candidate rule superset instead of reusing the on-disk cache.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational logging.")

    return parser.parse_args()


def print_paper_catalog() -> None:
    """Print the registered research paper benchmarks."""
    print("\nResearch Paper Benchmark Catalog")
    print("=" * 78)
    for key in list_available_papers():
        profile = PAPER_CATALOG[key]
        print(f"\n  [{key}]  {profile['title']}")
        print(f"      Authors : {profile['authors']}")
        print(f"      Venue   : {profile['venue']}")
        print(f"      DOI     : {profile['doi']}")
        print("      Targets : " + ", ".join(
            f"{k}={v}" for k, v in profile["target_metrics"].items()
        ))
    print("\n" + "=" * 78 + "\n")


def print_summary(result, paths) -> None:
    """Print the human-readable result banner."""
    paper = result.target_paper
    bar_width = 70

    print("\n" + "=" * bar_width)
    print("  HILL CLIMBING OPTIMIZATION SUMMARY")
    print("=" * bar_width)
    print(f"  Target Paper : [{paper['key']}] {paper['title']}")
    print(f"  Authors      : {paper['authors']}")
    print(f"  Venue        : {paper['venue']}  (DOI {paper['doi']})")
    print("-" * bar_width)
    print(f"  Fitness Mode : {result.config['fitness_mode']}")
    print(f"  Iterations   : {result.total_iterations_run} over "
          f"{result.config['max_restarts']} segment(s), "
          f"{result.restarts_triggered} restart(s) triggered")
    print(f"  Fitness      : {result.initial_fitness:.2f} -> {result.best_fitness:.2f} / 100")
    print(f"  Best Loss    : {result.best_loss:.6f}")
    print(f"  Termination  : {result.termination_reason}")
    print("-" * bar_width)
    print("  Target vs Achieved:")
    print(f"    {'Metric':<18}{'Target':>12}{'Achieved':>12}{'Error %':>12}")
    for metric, values in result.target_vs_achieved.items():
        print(f"    {metric:<18}{values['target']:>12.4f}"
              f"{values['achieved']:>12.4f}{values['error_pct']:>12.2f}")
    print("-" * bar_width)
    print("  Best Hyperparameters:")
    for name, value in result.best_state.to_dict().items():
        print(f"    - {name:<18}: {value}")
    print("-" * bar_width)
    print(f"  Execution Time: {result.execution_time_seconds:.2f}s")
    print("  Artifacts:")
    for name, path in paths.items():
        print(f"    - {name}: {path}")
    print("=" * bar_width + "\n")


def main() -> int:
    """Run the hill climbing search and write the optimization artifacts."""
    args = parse_args()

    if args.list_papers:
        print_paper_catalog()
        return 0

    setup_logger(verbose=args.verbose, quiet=args.quiet)

    # Fail fast and clearly on an unknown paper key before doing any mining.
    try:
        profile = get_paper_profile(args.target_paper)
    except (KeyError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    dataset = load_dataset(name_or_path=args.dataset)
    cleaned = clean_retail_data(
        df=dataset.raw_df,
        drop_cancellations=True,
        min_basket_size=2,
        country=args.country,
    )

    if cleaned.onehot_df.empty:
        print("[ERROR] No transactions remain after cleaning; cannot optimize.", file=sys.stderr)
        return 3

    climber = HillClimber(
        target_paper=args.target_paper,
        fitness_mode=args.fitness_mode,
        iterations=args.iterations,
        max_restarts=args.restarts,
        neighbors_per_step=args.neighbors,
        initial_step_size=args.step_size,
        stagnation_limit=args.stagnation_limit,
        scout_samples=args.scout,
        beta=args.beta,
        seed=args.seed,
        algorithm=args.algorithm,
        cache_dir=None if args.no_cache else str(ARTIFACTS_DIR / ".cache"),
    )

    result = climber.run(cleaned.onehot_df)

    paths = export_all(
        result,
        log_path=args.output_log,
        history_path=args.output_history,
        rules_path=args.output_rules,
        dataset_name=dataset.name,
    )

    if not args.quiet:
        print_summary(result, paths)

    return 0


if __name__ == "__main__":
    sys.exit(main())
