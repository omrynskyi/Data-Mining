"""CRISP-DM Phase 4 -- reproducible-ml skill: seed / environment / data pinning.

Exposes:
    set_all_seeds(seed)     -> seeds Python, NumPy, PyTorch (CPU+MPS/CUDA)
    sha256_of(path)         -> hex digest, for pinning the raw dataset
    capture_environment()   -> writes artifacts/env_snapshot.txt (pip freeze)
    assert_dataset_pinned() -> raises if data/Telco-Customer-Churn.csv drifted

Run directly to (a) write the environment snapshot, (b) verify the dataset
hash against data/processed/dataset_meta.json, and (c) PROVE determinism by
training the same small model twice from a fresh seed and diffing metrics
bit-for-bit.
"""
import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "Telco-Customer-Churn.csv"
META_PATH = ROOT / "data" / "processed" / "dataset_meta.json"
ENV_SNAPSHOT = ROOT / "artifacts" / "env_snapshot.txt"

DEFAULT_SEED = 42


def set_all_seeds(seed: int = DEFAULT_SEED) -> None:
    """Seed every RNG this project touches. Call this FIRST in every script.

    Covers the reproducible-ml skill's Pillar 1. torch is imported lazily so
    that non-torch scripts (sklearn/optuna only) don't pay the import cost
    or fail if torch is somehow unavailable.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        # MPS (Apple Silicon) has its own generator; there is no cudnn-style
        # determinism switch for it as of torch 2.8 -- this is one of the
        # documented determinism gotchas we call out below.
        if torch.backends.mps.is_available():
            torch.mps.manual_seed(seed)
    except ImportError:
        pass


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_dataset_pinned() -> str:
    """Verify the raw dataset on disk matches the hash pinned by Phase 3.

    This is the reproducible-ml "version the data" pillar: every downstream
    script can call this and know it is training on the exact bytes the
    business-metrics / EDA / feature-engineering phases analyzed.
    """
    meta = json.loads(META_PATH.read_text())
    pinned = meta["raw_sha256"]
    actual = sha256_of(DATA_RAW)
    if actual != pinned:
        raise RuntimeError(
            f"Dataset drift detected! pinned={pinned} actual={actual}. "
            "Refusing to train on an unpinned dataset."
        )
    return actual


def capture_environment() -> Path:
    """Write pip freeze + interpreter + platform info to artifacts/env_snapshot.txt."""
    lines = [
        f"python_executable: {sys.executable}",
        f"python_version: {sys.version.replace(chr(10), ' ')}",
        f"platform: {sys.platform}",
    ]
    try:
        import torch
        lines.append(f"torch_version: {torch.__version__}")
        lines.append(f"torch_mps_available: {torch.backends.mps.is_available()}")
        lines.append(f"torch_cuda_available: {torch.cuda.is_available()}")
    except ImportError:
        lines.append("torch: not importable")

    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True
    ).stdout

    ENV_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_SNAPSHOT, "w") as f:
        f.write("\n".join(lines) + "\n\n# pip freeze\n" + freeze)
    return ENV_SNAPSHOT


def _determinism_proof() -> dict:
    """Train the same tiny pipeline twice from a fresh process-level seed
    and prove the metrics are bit-identical. This is the skill's core claim
    ("same code + same data + same config -> same result") and we don't get
    to just assert it -- we run it twice and diff.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    sys.path.insert(0, str(ROOT / "src"))
    import pandas as pd
    from p3_pipeline import build_preprocessor

    train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
    X = train.drop(columns=["customerID", "Churn"])
    y = train["Churn"]

    def run_once():
        set_all_seeds(DEFAULT_SEED)
        Xtr, Xval, ytr, yval = train_test_split(
            X, y, test_size=0.2, random_state=DEFAULT_SEED, stratify=y
        )
        pipe = build_preprocessor()
        Xtr_t = pipe.fit_transform(Xtr)
        Xval_t = pipe.transform(Xval)
        clf = LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED)
        clf.fit(Xtr_t, ytr)
        proba = clf.predict_proba(Xval_t)[:, 1]
        auc = roc_auc_score(yval, proba)
        coef_hash = hashlib.sha256(clf.coef_.tobytes()).hexdigest()
        return auc, coef_hash, proba[:5].tolist()

    auc1, hash1, head1 = run_once()
    auc2, hash2, head2 = run_once()

    result = {
        "run1_auc": auc1,
        "run2_auc": auc2,
        "auc_bit_identical": bool(auc1 == auc2),
        "run1_coef_sha256": hash1,
        "run2_coef_sha256": hash2,
        "coef_bit_identical": bool(hash1 == hash2),
        "run1_first5_proba": head1,
        "run2_first5_proba": head2,
    }
    return result


if __name__ == "__main__":
    set_all_seeds(DEFAULT_SEED)

    print("== Dataset pinning ==")
    actual_hash = assert_dataset_pinned()
    print(f"raw dataset sha256 OK: {actual_hash}")

    print("\n== Environment snapshot ==")
    path = capture_environment()
    print(f"wrote {path}")

    print("\n== Determinism proof (train same pipeline twice) ==")
    proof = _determinism_proof()
    for k, v in proof.items():
        print(f"  {k}: {v}")

    out = ROOT / "artifacts" / "repro_determinism_proof.json"
    out.write_text(json.dumps(proof, indent=2))
    print(f"\nwrote {out}")

    assert proof["auc_bit_identical"] and proof["coef_bit_identical"], (
        "Determinism proof FAILED -- seeding is not fully covering this pipeline."
    )
    print("\nPASS: identical seed -> bit-identical result across two independent runs.")
