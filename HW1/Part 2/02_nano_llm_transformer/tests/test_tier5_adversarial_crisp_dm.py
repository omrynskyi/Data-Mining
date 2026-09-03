"""
Tier 5 Adversarial Test Suite: CRISP-DM State Machine Fuzzing & Telemetry Stress Harness.

Adversarial Objectives:
1. Rapid continuous lifecycle cycles (not_started -> running -> completed -> failed -> reset).
2. Out-of-order and non-sequential stage transitions (e.g. jumping from stage 1 to stage 6).
3. High concurrency stress with multiple simultaneous reader and writer threads.
4. Telemetry load: large volumes of log entries, deep artifact nesting, and JSON export validation.
5. Fuzzing with invalid, empty, or malicious stage IDs.
6. Mathematical duration consistency audits (start_time <= end_time, duration >= 0).
"""

import concurrent.futures
import time
from typing import Dict, Any, List
import pytest

from dashboard.crisp_dm import CrispDMTracker, StageStatus, DEFAULT_STAGES


@pytest.fixture
def fresh_tracker() -> CrispDMTracker:
    """Returns a newly initialized, clean CRISP-DM tracker."""
    tracker = CrispDMTracker()
    tracker.reset()
    return tracker


# ===========================================================================
# 1. State Machine Fuzzing & Rapid Lifecycle Cycles
# ===========================================================================

def test_adversarial_state_machine_rapid_cycling(fresh_tracker: CrispDMTracker):
    """
    Stress-test: 50 consecutive full lifecycle iterations across all 6 stages.
    Audits state invariants, timestamp consistency, and reset behavior.
    """
    stage_keys = [s["id"] for s in DEFAULT_STAGES]

    for cycle in range(50):
        # 1. Start all stages
        for s_id in stage_keys:
            fresh_tracker.start_stage(s_id)
            stage = fresh_tracker.get_stage(s_id)
            assert stage["status"] == StageStatus.RUNNING.value
            assert stage["start_time"] is not None
            assert stage["end_time"] is None

        # 2. Complete half, fail half
        for idx, s_id in enumerate(stage_keys):
            if idx % 2 == 0:
                fresh_tracker.complete_stage(s_id, metrics={"cycle": cycle, "val": idx * 1.5})
                stage = fresh_tracker.get_stage(s_id)
                assert stage["status"] == StageStatus.COMPLETED.value
            else:
                fresh_tracker.fail_stage(s_id, error=f"Fuzzed failure in cycle {cycle}")
                stage = fresh_tracker.get_stage(s_id)
                assert stage["status"] == StageStatus.FAILED.value

            assert stage["end_time"] is not None
            assert stage["end_time"] >= stage["start_time"]
            assert stage["duration_seconds"] >= 0.0

        # 3. Reset and verify initial state
        fresh_tracker.reset()
        for s_id in stage_keys:
            st = fresh_tracker.get_stage(s_id)
            assert st["status"] == StageStatus.NOT_STARTED.value
            assert st["start_time"] is None
            assert st["end_time"] is None
            assert st["duration_seconds"] is None
            assert st["metrics"] == {}
            assert st["logs"] == []


# ===========================================================================
# 2. Out-of-Order & Non-Sequential Transitions
# ===========================================================================

def test_adversarial_out_of_order_stage_progression(fresh_tracker: CrispDMTracker):
    """
    Tests jumping between arbitrary non-adjacent stages:
    e.g. Deployment -> Data Understanding -> Evaluation -> Business Understanding.
    Verifies that the state machine does not lock up or corrupt internal dictionaries.
    """
    # Jump directly to stage 6 (Deployment)
    fresh_tracker.start_stage("deployment")
    assert fresh_tracker.current_stage == "deployment"
    fresh_tracker.complete_stage("deployment", metrics={"deployed_version": "v1.0.0"})

    # Jump backwards to stage 2 (Data Understanding)
    fresh_tracker.start_stage("data_understanding")
    assert fresh_tracker.current_stage == "data_understanding"
    fresh_tracker.fail_stage("data_understanding", error="Missing raw data source")

    # Complete stage 4 (Modeling) without starting it explicitly (direct completion)
    fresh_tracker.complete_stage("modeling", metrics={"loss": 0.42})
    stage_mod = fresh_tracker.get_stage("modeling")
    assert stage_mod["status"] == StageStatus.COMPLETED.value
    assert stage_mod["duration_seconds"] >= 0.0
    assert stage_mod["metrics"]["loss"] == 0.42

    # Verify overall exported state remains intact
    exported = fresh_tracker.export_state()
    assert exported["status"] == "ok"
    assert len(exported["stages"]) == 6


# ===========================================================================
# 3. Invalid & Malicious Stage ID Handling
# ===========================================================================

@pytest.mark.parametrize("invalid_id", [
    "",
    "   ",
    "non_existent_stage_123",
    "null",
    "DROP TABLE stages;",
    "../../etc/passwd",
    "🚀🔥🧠",
    "None",
])
def test_adversarial_invalid_stage_id_robustness(fresh_tracker: CrispDMTracker, invalid_id: str):
    """
    Tests that querying, starting, completing, failing, or logging invalid stage IDs
    does not cause uncaught exceptions or pollute the tracked stage registry.
    """
    # 1. get_stage on invalid ID
    res = fresh_tracker.get_stage(invalid_id)
    assert res is None

    # 2. Mutations on invalid IDs should be no-ops
    fresh_tracker.start_stage(invalid_id)
    fresh_tracker.complete_stage(invalid_id, metrics={"key": "val"})
    fresh_tracker.fail_stage(invalid_id, error="Error message")
    fresh_tracker.log_stage(invalid_id, "Log message")
    fresh_tracker.add_artifact(invalid_id, "artifact_key", "artifact_val")

    # Registry size must remain exactly 6
    assert len(fresh_tracker.stages) == 6
    assert invalid_id not in fresh_tracker.stages


# ===========================================================================
# 4. Multithreaded Concurrent Tracker Mutations
# ===========================================================================

def test_adversarial_concurrent_tracker_mutations(fresh_tracker: CrispDMTracker):
    """
    Tests race condition safety under 30 concurrent threads writing logs,
    updating metrics, adding artifacts, and transitioning statuses simultaneously.
    """
    stages = [s["id"] for s in DEFAULT_STAGES]

    def worker_task(thread_id: int):
        s_id = stages[thread_id % len(stages)]
        fresh_tracker.log_stage(s_id, f"Thread {thread_id} log entry")
        fresh_tracker.add_artifact(s_id, f"artifact_t{thread_id}", f"value_{thread_id}")
        if thread_id % 3 == 0:
            fresh_tracker.start_stage(s_id)
        elif thread_id % 3 == 1:
            fresh_tracker.complete_stage(s_id, metrics={f"m_t{thread_id}": thread_id})
        else:
            fresh_tracker.fail_stage(s_id, error=f"Thread {thread_id} simulated error")
        return fresh_tracker.export_state()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_task, i) for i in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 30
    final_state = fresh_tracker.export_state()
    assert final_state["status"] == "ok"
    assert len(final_state["stages"]) == 6


# ===========================================================================
# 5. Heavy Telemetry Load & Serialization Validation
# ===========================================================================

def test_adversarial_massive_log_and_artifact_load(fresh_tracker: CrispDMTracker):
    """
    Stress-test: Appends 1,000 log lines and 200 artifact entries to a single stage.
    Verifies that export_state serializes cleanly without memory bloat or truncation error.
    """
    stage_id = "modeling"
    fresh_tracker.start_stage(stage_id)

    # 1. 1,000 log messages
    for i in range(1000):
        fresh_tracker.log_stage(stage_id, f"Epoch {i}: loss={1.0 / (i + 1):.6f}, lr=3e-4")

    # 2. 200 artifact entries
    for j in range(200):
        fresh_tracker.add_artifact(stage_id, f"checkpoint_step_{j * 100}", {"step": j * 100, "val_loss": 0.5})

    fresh_tracker.complete_stage(stage_id, metrics={"final_loss": 0.001, "total_epochs": 1000})

    stage = fresh_tracker.get_stage(stage_id)
    assert len(stage["logs"]) == 1000
    assert len(stage["artifacts"]) == 200
    assert stage["status"] == StageStatus.COMPLETED.value

    # Validate full export dictionary structure
    exported = fresh_tracker.export_state()
    assert exported["status"] == "ok"
    assert "updated_at" in exported
    assert len(exported["stages"][stage_id]["logs"]) == 1000
