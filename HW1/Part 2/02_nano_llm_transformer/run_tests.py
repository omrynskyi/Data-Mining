#!/usr/bin/env python3
"""
Master Test Suite Orchestrator & CLI Runner.

Executes all 5 test tiers and root acceptance scripts with comprehensive reporting.

Usage:
    python run_tests.py                     # Run full multi-tier suite + acceptance
    python run_tests.py --tier 1            # Run Tier 1 Feature Coverage tests
    python run_tests.py --tier 2            # Run Tier 2 Boundary & Corner Cases tests
    python run_tests.py --tier 3            # Run Tier 3 Combinations tests
    python run_tests.py --tier 4            # Run Tier 4 Workloads tests
    python run_tests.py --tier 5            # Run Tier 5 Adversarial tests
    python run_tests.py --acceptance        # Run root acceptance scripts only
    python run_tests.py --json-report       # Generate JSON telemetry artifact
"""

import sys
import os
import time
import argparse
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_command_suite(name: str, cmd: List[str]) -> Dict[str, Any]:
    print(f"\n>>> Running: {name} ...")
    print(f"    Command: {' '.join(cmd)}")
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    t1 = time.perf_counter()
    duration = t1 - t0
    
    passed = proc.returncode == 0
    status_str = "PASS" if passed else "FAIL"
    print(f"    Result : {status_str} (Exit code {proc.returncode}) in {duration:.2f}s")
    
    if not passed:
        print("\n--- STDOUT ---")
        print(proc.stdout)
        print("--- STDERR ---")
        print(proc.stderr)
        print("-" * 40)
    else:
        # Print snippet of output if concise
        lines = [line for line in proc.stdout.strip().split("\n") if line.strip()]
        if lines:
            print(f"    Summary: {lines[-1]}")

    return {
        "suite_name": name,
        "command": cmd,
        "exit_code": proc.returncode,
        "passed": passed,
        "duration_seconds": round(duration, 3),
        "stdout": proc.stdout,
        "stderr": proc.stderr
    }


def main():
    parser = argparse.ArgumentParser(description="Master Test Runner for Nano LLM & Admin Dashboard")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "5", "all"], default="all",
                        help="Select test tier to execute (default: all)")
    parser.add_argument("--acceptance", action="store_true",
                        help="Execute standalone root acceptance scripts only")
    parser.add_argument("--json-report", action="store_true",
                        help="Export JSON test report to test_report.json")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose test execution output")
    args = parser.parse_args()

    print("=" * 80)
    print(" NANO LLM TRANSFORMER & ADMIN DASHBOARD - E2E TEST RUNNER")
    print("=" * 80)
    print(f" Project Root : {PROJECT_ROOT}")
    print(f" Target Mode  : {'Acceptance Scripts' if args.acceptance else f'Tier {args.tier}'}")

    suite_results = []
    py_exec = sys.executable

    pytest_base = [py_exec, "-m", "pytest"]
    if args.verbose:
        pytest_base.append("-v")

    if args.acceptance:
        # Run root acceptance scripts
        suite_results.append(run_command_suite("Acceptance 1: Model Architecture & SFT Gradients", [py_exec, "test_model.py"]))
        suite_results.append(run_command_suite("Acceptance 2: Dashboard Endpoints & CRISP-DM Tracker", [py_exec, "test_dashboard.py"]))
        suite_results.append(run_command_suite("Acceptance 3: Apple Silicon MPS Generation & Memory Limit", [py_exec, "benchmark_mps.py"]))
    else:
        # Tiers execution
        if args.tier in ["1", "all"]:
            suite_results.append(run_command_suite(
                "Tier 1: Feature Coverage (>=5 tests per feature)",
                pytest_base + ["tests/test_tier1_features.py"]
            ))
        if args.tier in ["2", "all"]:
            suite_results.append(run_command_suite(
                "Tier 2: Boundary & Corner Cases (>=5 tests per feature)",
                pytest_base + ["tests/test_tier2_boundaries.py"]
            ))
        if args.tier in ["3", "all"]:
            suite_results.append(run_command_suite(
                "Tier 3: Combinatorial & Cross-Feature Interactions",
                pytest_base + ["tests/test_tier3_combinations.py"]
            ))
        if args.tier in ["4", "all"]:
            suite_results.append(run_command_suite(
                "Tier 4: Real-World Workloads & E2E Simulations",
                pytest_base + ["tests/test_tier4_workloads.py"]
            ))
        if args.tier in ["5", "all"]:
            suite_results.append(run_command_suite(
                "Tier 5: Adversarial Stress & Empirical Fuzzing",
                pytest_base + [
                    "tests/test_tier5_adversarial_challenge.py",
                    "tests/test_tier5_adversarial_crisp_dm.py",
                    "tests/test_tier5_adversarial_dashboard.py",
                    "tests/test_tier5_adversarial_mps_memory.py",
                ]
            ))
        if args.tier == "all":
            suite_results.append(run_command_suite("Root Acceptance: Model Verification", [py_exec, "test_model.py"]))
            suite_results.append(run_command_suite("Root Acceptance: Dashboard Verification", [py_exec, "test_dashboard.py"]))
            suite_results.append(run_command_suite("Root Acceptance: MPS Benchmark", [py_exec, "benchmark_mps.py"]))

    # Summary calculation
    total_suites = len(suite_results)
    passed_suites = sum(1 for s in suite_results if s["passed"])
    failed_suites = total_suites - passed_suites
    total_duration = sum(s["duration_seconds"] for s in suite_results)

    print("\n" + "=" * 80)
    print(" EXECUTIVE TEST SUITE SUMMARY")
    print("=" * 80)
    for s in suite_results:
        status_tag = "[ PASS ]" if s["passed"] else "[ FAIL ]"
        print(f" {status_tag} {s['suite_name']:<60} ({s['duration_seconds']:.2f}s)")
    print("-" * 80)
    print(f" Total Suites: {total_suites} | Passed: {passed_suites} | Failed: {failed_suites} | Total Time: {total_duration:.2f}s")
    
    if args.json_report:
        report_path = PROJECT_ROOT / "test_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "total_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "total_duration_seconds": round(total_duration, 3),
                "suites": suite_results
            }, f, indent=2)
        print(f" [i] Exported JSON report to: {report_path}")

    print("=" * 80)
    if failed_suites == 0:
        print(" 🎉 ALL TEST SUITES PASSED SUCCESSFULLY (100% PASS RATE)")
        print("=" * 80)
        sys.exit(0)
    else:
        print(f" ❌ {failed_suites} TEST SUITE(S) FAILED")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
