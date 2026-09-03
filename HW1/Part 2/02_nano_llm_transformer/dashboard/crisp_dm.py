"""CRISP-DM Pipeline Tracker and State Machine for Nano LLM Data Science Lifecycle."""

import time
from enum import Enum
from typing import Dict, Any, List, Optional


class StageStatus(str, Enum):
    """Standardized lifecycle status for CRISP-DM stages."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


DEFAULT_STAGES = [
    {
        "id": "business_understanding",
        "name": "Business Understanding",
        "order": 1,
        "description": "Formulate compute budget, architecture constraints (4GB UMA limit), target perplexity, and use-case scope.",
    },
    {
        "id": "data_understanding",
        "name": "Data Understanding",
        "order": 2,
        "description": "Analyze raw corpus statistics, character distributions, vocabulary coverage, and token entropy.",
    },
    {
        "id": "data_preparation",
        "name": "Data Preparation",
        "order": 3,
        "description": "Byte/BPE tokenizer training, sequence chunking, train/validation splitting, and SFT prompt-masking collation.",
    },
    {
        "id": "modeling",
        "name": "Modeling",
        "order": 4,
        "description": "Nano Transformer architecture instantiation (RoPE, SwiGLU, RMSNorm), forward-backward gradient flow, and SFT training.",
    },
    {
        "id": "evaluation",
        "name": "Evaluation",
        "order": 5,
        "description": "Validation loss tracking, perplexity computation, KV-cache speedup benchmarks, and generation quality validation.",
    },
    {
        "id": "deployment",
        "name": "Deployment",
        "order": 6,
        "description": "FastAPI dashboard server launch, live KV-cache & attention heatmaps inspection, and Apple Silicon MPS profiling.",
    },
]


class CrispDMTracker:
    """Manages end-to-end CRISP-DM 6-phase pipeline state and telemetry."""

    def __init__(self) -> None:
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.current_stage: str = "business_understanding"
        self.active_pipeline: bool = True
        self.reset()

    def reset(self) -> None:
        """Resets all stages to initial not_started status."""
        self.stages = {}
        for s in DEFAULT_STAGES:
            stage_id = s["id"]
            self.stages[stage_id] = {
                "id": stage_id,
                "name": s["name"],
                "order": s["order"],
                "description": s["description"],
                "status": StageStatus.NOT_STARTED.value,
                "start_time": None,
                "end_time": None,
                "duration_seconds": None,
                "metrics": {},
                "artifacts": {},
                "logs": [],
            }
        self.current_stage = "business_understanding"
        self.active_pipeline = True

    def get_stages(self) -> Dict[str, Dict[str, Any]]:
        """Returns dictionary of all tracked stages."""
        return self.stages

    def get_stage(self, stage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves state of a specific stage by ID, returning None if not found."""
        return self.stages.get(stage_id, None)

    def start_stage(self, stage_id: str) -> None:
        """Marks a stage as running and records start timestamp."""
        if stage_id not in self.stages:
            return
        stage = self.stages[stage_id]
        stage["status"] = StageStatus.RUNNING.value
        stage["start_time"] = time.time()
        stage["end_time"] = None
        stage["duration_seconds"] = None
        self.current_stage = stage_id

    def complete_stage(
        self,
        stage_id: str,
        metrics: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None
    ) -> None:
        """Marks a stage as completed and records metrics, artifacts, and duration."""
        if stage_id not in self.stages:
            return
        stage = self.stages[stage_id]
        now = time.time()
        start = stage.get("start_time")
        if start is None:
            stage["start_time"] = now
            duration = 0.0
        else:
            duration = max(0.0, now - start)

        stage["status"] = StageStatus.COMPLETED.value
        stage["end_time"] = now
        stage["duration_seconds"] = round(duration, 4)

        if metrics:
            stage["metrics"].update(metrics)
        if artifacts:
            stage["artifacts"].update(artifacts)

    def fail_stage(self, stage_id: str, error: str) -> None:
        """Marks a stage as failed and logs the error."""
        if stage_id not in self.stages:
            return
        stage = self.stages[stage_id]
        now = time.time()
        start = stage.get("start_time")
        duration = (now - start) if start else 0.0

        stage["status"] = StageStatus.FAILED.value
        stage["end_time"] = now
        stage["duration_seconds"] = round(duration, 4)
        stage["logs"].append(f"ERROR: {error}")

    def log_stage(self, stage_id: str, message: str) -> None:
        """Appends a log line to the specified stage."""
        if stage_id in self.stages:
            self.stages[stage_id]["logs"].append(message)

    def add_artifact(self, stage_id: str, key: str, value: Any) -> None:
        """Adds an artifact key-value entry to the specified stage."""
        if stage_id in self.stages:
            self.stages[stage_id]["artifacts"][key] = value

    def export_state(self) -> Dict[str, Any]:
        """Exports complete serializable pipeline state."""
        return {
            "status": "ok",
            "current_stage": self.current_stage,
            "active_pipeline": self.active_pipeline,
            "stages": self.stages,
            "updated_at": round(time.time(), 3),
        }
