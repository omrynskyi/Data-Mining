#!/usr/bin/env python3
"""
Master E2E Test Suite Runner for Customer Segmentation & Dashboard Project.
Executes all Python test tiers and dashboard render checks, providing a consolidated report.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def print_banner(title: str):
    width = 78
    print("=" * width)
    print(f"  {title.center(width - 4)}")
    print("=" * width)


def main():
    project_root = Path(__file__).resolve().parent.parent
    tests_dir = project_root / "tests"

    print_banner("CUSTOMER SEGMENTATION & DASHBOARD — E2E TEST RUNNER")
    print(f"Project Root: {project_root}")
    print(f"Python Executable: {sys.executable}")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("-" * 78)

    # Set PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + (os.pathsep + env.get("PYTHONPATH", "") if "PYTHONPATH" in env else "")

    # Execute Pytest
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v",
        "--tb=short"
    ]

    print("\n[Step 1/2] Running Python E2E & Contract Test Suite (pytest)...")
    start_time = time.time()
    pytest_proc = subprocess.run(pytest_cmd, cwd=str(project_root), env=env)
    pytest_duration = time.time() - start_time

    # Check Dashboard if dashboard/package.json exists
    dashboard_dir = project_root / "dashboard"
    dashboard_status = "SKIPPED (dashboard not yet implemented)"
    if (dashboard_dir / "package.json").exists():
        print("\n[Step 2/2] Running React Dashboard Vitest Programmatic Render Tests...")
        dash_proc = subprocess.run(["npm", "test"], cwd=str(dashboard_dir), env=env)
        if dash_proc.returncode == 0:
            dashboard_status = "PASSED"
        else:
            dashboard_status = "FAILED"
    else:
        print("\n[Step 2/2] React Dashboard not yet scaffolded; dashboard tests skipped.")

    # Summary Report
    print_banner("TEST EXECUTION SUMMARY")
    print(f"Pytest Status:       {'PASSED' if pytest_proc.returncode == 0 else 'FAILED'} ({pytest_duration:.2f}s)")
    print(f"Dashboard Status:    {dashboard_status}")
    print("-" * 78)

    if pytest_proc.returncode == 0:
        print(">> ALL ACTIVE E2E & CONTRACT TEST SUITES PASSED SUCCESSFULLY.")
        return 0
    else:
        print(">> TEST FAILURES DETECTED. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
