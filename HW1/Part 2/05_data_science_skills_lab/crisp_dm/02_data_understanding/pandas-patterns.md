---
skill: pandas-patterns
pack: param087/agent-ml-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - src/p2_pandas_patterns.py
  - artifacts/pandas_patterns/pandas_patterns_results.json
---

## What the skill prescribes

A code-quality skill, not an analysis workflow: idiomatic, vectorized, memory-efficient pandas.
Core rules — assign with `.loc` not chained indexing, vectorize instead of `apply(axis=1)`,
`np.select`/`np.where` for conditional columns, downcast dtypes (`category`, `int32`/`float32`)
for memory, prefer `merge` with `validate=` over loops, and use `groupby(...).transform()` where
a join-back aggregate is needed instead of a merge round-trip.

## Applied to Telco churn

Four real before/after refactors, run on the full 7,043-row dataset, each with correctness
verified (`assert ... .equals(...)` / `np.allclose`) before any speed claim, and timed with
`timeit` (`src/p2_pandas_patterns.py`):

**1. Chained indexing vs `.loc`:** `df[mask]['col'] = value` actually raised
**1 `SettingWithCopyWarning`** when run against this DataFrame, confirming the risk is real, not
theoretical — its effect on the original frame is undefined. The `.loc[mask, 'col'] = value`
version is unambiguous and was verified to produce the correct segment counts
(2,096 tenure>24 rows tagged "veteran", 4,947 tagged "new").

**2. `apply(axis=1)` vs vectorized** (a 4-rule risk-scoring feature: contract type, internet
type, tenure, paperless billing): both versions verified to produce **identical** Series.
Measured over 5 repeats: `apply` **70.87 ms**, vectorized **1.239 ms** — **57.2x speedup**.

**3. `object` -> `category` dtype memory reduction** (16 low-cardinality string columns,
2-4 distinct values each): measured with `memory_usage(deep=True)` before/after, not estimated.
Whole DataFrame: **7.780 MB -> 0.815 MB (89.5% reduction)**. The 16 downcast columns alone:
**7.083 MB -> 0.117 MB (98.3% reduction)**.

**4. `groupby().transform()` vs `merge`** (join back each row's contract-type average
`MonthlyCharges`): both versions verified to produce numerically identical values
(`np.allclose`). Measured over 20 repeats: merge **4.615 ms**, `transform` **0.448 ms** —
**10.3x speedup**, while also avoiding the `reset_index()`/rename bookkeeping and the silent
row-count-change risk an unvalidated merge carries.

## Outputs produced

- `src/p2_pandas_patterns.py` — all 4 before/after pairs, correctness-asserted, `timeit`-measured
- `artifacts/pandas_patterns/pandas_patterns_results.json` — measured speedups and memory
  numbers for all 4 patterns
