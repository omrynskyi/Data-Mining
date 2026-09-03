"""Run the PetFinder adoption-speed pipeline end-to-end.

`pipeline/` now holds only the scripts on the dependency path to the current
final model (a CatBoost ordinal regression, optimized-threshold decoding)
and its evaluation/interpretability artifacts. This runs them all, in order,
phase by phase. Each step's combined stdout/stderr is streamed to the
console and saved to `logs/<script>.log` (overwriting any previous log for
that step). Stops at the first failing step, since every later step assumes
earlier ones succeeded. Total runtime is roughly 10-15 minutes.

The full historical record — every ablation, the hyperparameter search, the
ResNet18-vs-CLIP comparison, the superseded multiclass model — lives in
`archived/` at the repo root, one directory up from here, and is not part of
this runner; see that folder's own scripts (each still runnable — they add
`pipeline/` to `sys.path` themselves) or `crisp_dm_notes/04_modeling.md` for
why each experiment was tried and what it found.

Examples
--------
    python3 run_pipeline.py --dry-run            # show the plan, run nothing
    python3 run_pipeline.py --phase 3            # just data preparation
    python3 run_pipeline.py --from train_ordinal_regression.py  # resume
    python3 run_pipeline.py                      # everything, in order
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
LOG_DIR = PIPELINE_DIR / "logs"


@dataclass
class Step:
    script: str
    phase: int
    note: str


# Order matches the README's Walkthrough section exactly.
STEPS: list[Step] = [
    # Phase 3 — Data preparation
    Step("build_stage1_feature_table.py", 3, "builds data/listing_features_stage1.csv"),
    Step("build_image_pixel_features.py", 3, "builds data/listing_features_stage2.csv"),
    Step("build_image_embedding_features.py", 3, "frozen ResNet18 embeddings (the backbone actually used)"),
    # Phase 4 — Modeling
    Step("train_ordinal_regression.py", 4, "the winning reformulation"),
    Step("generate_ordinal_model_artifacts.py", 4, "current final model's OOF predictions + importances"),
    # Phase 5 — Evaluation
    Step("evaluate_ordinal_model.py", 5, "error analysis for the current final model"),
    Step("analyze_model_shap.py", 5, "SHAP direction analysis"),
    Step("create_shap_charts.py", 5, "renders the 5 SHAP charts"),
    Step("create_model_comparison_table.py", 5, "summary table used in Findings.md"),
    Step("create_class_recall_table.py", 5, "summary table used in Findings.md"),
]


def run_step(step: Step) -> float:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / (Path(step.script).stem + ".log")
    print(f"\n{'=' * 70}\n>>> [Phase {step.phase}] {step.script}  ({step.note})\n{'=' * 70}")

    start = time.time()
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            [sys.executable, step.script],
            cwd=PIPELINE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)
        process.wait()
    elapsed = time.time() - start

    if process.returncode != 0:
        print(f"\n!!! {step.script} FAILED (exit {process.returncode}) after {elapsed:.0f}s — see {log_path}")
        raise SystemExit(1)
    print(f"--- {step.script} done in {elapsed:.0f}s")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", type=int, action="append", choices=[3, 4, 5], help="restrict to phase(s); repeatable")
    parser.add_argument("--from", dest="from_script", help="resume starting at this script (skip everything before it)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit without running anything")
    args = parser.parse_args()

    steps = STEPS
    if args.phase:
        steps = [s for s in steps if s.phase in args.phase]
    if args.from_script:
        names = [s.script for s in steps]
        if args.from_script not in names:
            parser.error(f"--from {args.from_script!r} is not in the selected step list")
        steps = steps[names.index(args.from_script):]

    if not steps:
        parser.error("no steps selected — check --phase/--from")

    print(f"Planned steps ({len(steps)}), total runtime roughly 10-15 min if not filtered further:")
    for s in steps:
        print(f"  [Phase {s.phase}] {s.script:<40} — {s.note}")

    if args.dry_run:
        print("\n--dry-run: not executing anything.")
        return

    overall_start = time.time()
    timings: list[tuple[str, float]] = []
    for step in steps:
        elapsed = run_step(step)
        timings.append((step.script, elapsed))

    total = time.time() - overall_start
    print(f"\n{'=' * 70}\nAll {len(steps)} steps completed in {total / 60:.1f} min.\n{'=' * 70}")
    for name, elapsed in timings:
        print(f"  {name:<40} {elapsed:6.0f}s")


if __name__ == "__main__":
    main()
