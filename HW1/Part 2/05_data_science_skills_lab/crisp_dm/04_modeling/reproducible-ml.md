---
skill: reproducible-ml
pack: param087/agent-ml-skills
crisp_dm_phase: 4 - Modeling
artifacts: [src/p4_repro.py, artifacts/env_snapshot.txt, artifacts/repro_determinism_proof.json]
---

# reproducible-ml — Telco Churn Modeling

## What the skill prescribes

Three pillars: **seed everything** (Python `random`, NumPy, PyTorch CPU/CUDA/MPS,
`PYTHONHASHSEED`), **pin the environment** (exact package versions + interpreter/
platform recorded per run), and **version the data** (hash the raw file, never
overwrite it in place, key runs to the hash). It also lists concrete determinism
gotchas (GPU reduction nondeterminism, parallel groupby ordering, unset
`PYTHONHASHSEED`, unpinned deps) and says: don't just assert reproducibility,
prove it — same code + same data + same config must literally reproduce the
same result.

## Applied to Telco churn

- `src/p4_repro.py` exposes `set_all_seeds(seed=42)`, imported and called first
  in every other `p4_*`/`p5_*` script in this phase, so the whole pipeline
  shares one seed discipline instead of each script inventing its own.
  `set_all_seeds` seeds `PYTHONHASHSEED`, `random`, `numpy`, and (lazily,
  so non-torch scripts don't pay the import cost) `torch.manual_seed`,
  `torch.cuda.manual_seed_all` + cudnn determinism flags, and
  `torch.mps.manual_seed` for Apple Silicon.
- **Dataset pinning**: `assert_dataset_pinned()` re-hashes
  `data/Telco-Customer-Churn.csv` with SHA-256 and compares it against the
  value Phase 3 recorded in `data/processed/dataset_meta.json`
  (`16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`).
  Verified independently with `shasum -a 256` — matches. Every `p4_*` script
  in this phase calls it before touching data, so silent dataset drift
  (e.g. someone re-downloading a different Kaggle snapshot) fails loudly
  instead of silently changing metrics.
- **Environment pinning**: `capture_environment()` writes
  `artifacts/env_snapshot.txt` — interpreter path/version, platform, torch
  version + MPS/CUDA availability, and a full `pip freeze`. This complements
  the already-pinned `requirements.txt` at the project root by recording
  what is *actually installed* at run time, not just what was requested.
- **Determinism proof (not just assertion)**: `_determinism_proof()` trains
  the identical pipeline (`p3_pipeline.build_preprocessor()` ->
  `LogisticRegression`) **twice** in the same process, each time starting
  from a fresh `set_all_seeds(42)` call and a fresh train/val split, and
  diffs the results bit-for-bit:
  - `run1_auc == run2_auc`: `0.8510978624400174` both times.
  - SHA-256 of the fitted `coef_` array: identical both runs
    (`a1bff3f4...`).
  - First 5 predicted probabilities: identical to full float precision.

  Both equality checks assert at the bottom of the script, so a future
  regression (e.g. someone adds an unseeded `np.random` call) fails the
  script instead of silently drifting.

## Determinism gotchas documented (per the skill's checklist)

- **MPS has no cudnn-style determinism switch.** On Apple Silicon (this
  machine), `torch.backends.mps.is_available()` is `True`, but unlike CUDA's
  `cudnn.deterministic`/`cudnn.benchmark` flags, there is no equivalent MPS
  toggle in torch 2.8. `set_all_seeds` seeds the MPS generator
  (`torch.mps.manual_seed`) but this is weaker than the CUDA guarantee —
  called out explicitly so the pytorch-training-loop MLP results are read
  with that caveat.
- **`PYTHONHASHSEED`** is set at the start of every script (affects
  `set`/`dict` iteration order across process runs, e.g. sklearn's OneHotEncoder
  category ordering in edge cases).
- **Unpinned deps**: `requirements.txt` pins every package with `==`;
  `env_snapshot.txt` proves what's actually resolved, catching cases where a
  pin was violated by a transitive dependency.
- **Data versioning**: `data/` is treated as append-only in this project
  (explicit constraint from the team lead) — the raw CSV is never edited in
  place, so the hash pin is a durable contract, not a one-time check.

## Outputs produced

- `src/p4_repro.py` — the reusable seeding/pinning/proof module, imported by
  downstream `p4_*`/`p5_*` scripts.
- `artifacts/env_snapshot.txt` — interpreter, platform, torch/MPS info, full `pip freeze`.
- `artifacts/repro_determinism_proof.json` — the two-run bit-identical comparison.
