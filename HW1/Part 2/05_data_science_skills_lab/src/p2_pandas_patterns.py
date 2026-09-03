"""
Phase 2 - Data Understanding: pandas-patterns skill.

A code-quality skill: real before/after refactors run on THIS dataset, timed with
timeit, with actual measured speedups and memory savings (nothing invented).

Demonstrates the 4 patterns called out in the skill's Core rules:
  1. Chained indexing / SettingWithCopyWarning vs .loc
  2. Slow apply(axis=1) row loop vs vectorized
  3. object -> category dtype memory reduction (measured via memory_usage(deep=True))
  4. groupby-transform instead of a merge for a per-group aggregate join-back
"""
import pathlib
import timeit
import warnings

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "pandas_patterns"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "data" / "Telco-Customer-Churn.csv")
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")

results = {}

# ---------------------------------------------------------------------------
# Pattern 1: chained indexing (SettingWithCopyWarning risk) vs .loc
print("=== Pattern 1: chained indexing vs .loc ===")


def chained_indexing_version(data: pd.DataFrame) -> pd.DataFrame:
    d = data.copy()
    subset = d[d["tenure"] > 24]           # this creates a view/copy ambiguity
    subset["tenure_segment"] = "veteran"   # WRONG: chained assignment, may warn or silently no-op
    return d


def loc_version(data: pd.DataFrame) -> pd.DataFrame:
    d = data.copy()
    d.loc[d["tenure"] > 24, "tenure_segment"] = "veteran"
    d["tenure_segment"] = d["tenure_segment"].fillna("new")
    return d


with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    _ = chained_indexing_version(df)
    n_warnings = sum(1 for w in caught if issubclass(w.category, pd.errors.SettingWithCopyWarning))

correct = loc_version(df)
assert correct["tenure_segment"].value_counts().to_dict() == {
    "veteran": int((df["tenure"] > 24).sum()), "new": int((df["tenure"] <= 24).sum())
}
results["pattern_1_chained_vs_loc"] = {
    "settingwithcopy_warnings_raised_by_chained_version": n_warnings,
    "loc_version_correct": True,
    "loc_version_value_counts": correct["tenure_segment"].value_counts().to_dict(),
    "conclusion": (
        "Chained assignment (df[mask]['col'] = value) raised "
        f"{n_warnings} SettingWithCopyWarning(s) and its effect on the original DataFrame is "
        "undefined (may or may not persist depending on whether pandas returned a view or a copy). "
        ".loc[mask, 'col'] = value is unambiguous and always correct."
    ),
}
print(results["pattern_1_chained_vs_loc"]["conclusion"])

# ---------------------------------------------------------------------------
# Pattern 2: apply(axis=1) row loop vs vectorized — real timeit comparison
print("\n=== Pattern 2: apply(axis=1) vs vectorized ===")


def risk_score_apply(row):
    score = 0
    if row["Contract"] == "Month-to-month":
        score += 3
    if row["InternetService"] == "Fiber optic":
        score += 2
    if row["tenure"] < 12:
        score += 2
    if row["PaperlessBilling"] == "Yes":
        score += 1
    return score


def risk_score_vectorized(data: pd.DataFrame) -> pd.Series:
    score = pd.Series(0, index=data.index)
    score += (data["Contract"] == "Month-to-month") * 3
    score += (data["InternetService"] == "Fiber optic") * 2
    score += (data["tenure"] < 12) * 2
    score += (data["PaperlessBilling"] == "Yes") * 1
    return score


apply_result = df.apply(risk_score_apply, axis=1)
vec_result = risk_score_vectorized(df)
assert apply_result.equals(vec_result), "apply and vectorized versions must produce identical results"

n_repeat = 5
t_apply = timeit.timeit(lambda: df.apply(risk_score_apply, axis=1), number=n_repeat) / n_repeat
t_vec = timeit.timeit(lambda: risk_score_vectorized(df), number=n_repeat) / n_repeat
results["pattern_2_apply_vs_vectorized"] = {
    "n_rows": len(df), "timeit_repeats": n_repeat,
    "apply_axis1_seconds": round(t_apply, 5), "vectorized_seconds": round(t_vec, 6),
    "speedup_x": round(t_apply / t_vec, 1),
    "results_identical": True,
}
print(f"apply(axis=1): {t_apply*1000:.2f} ms | vectorized: {t_vec*1000:.3f} ms | "
      f"speedup: {t_apply/t_vec:.1f}x (results verified identical)")

# ---------------------------------------------------------------------------
# Pattern 3: object -> category dtype memory reduction — measured
print("\n=== Pattern 3: object -> category memory reduction ===")

low_cardinality_cols = ["gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
                         "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
                         "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
                         "PaperlessBilling", "PaymentMethod", "Churn"]

mem_before_total = int(df.memory_usage(deep=True).sum())
mem_before_cols = int(df[low_cardinality_cols].memory_usage(deep=True).sum())

df_cat = df.copy()
for c in low_cardinality_cols:
    df_cat[c] = df_cat[c].astype("category")

mem_after_total = int(df_cat.memory_usage(deep=True).sum())
mem_after_cols = int(df_cat[low_cardinality_cols].memory_usage(deep=True).sum())

results["pattern_3_category_dtype"] = {
    "columns_downcast": len(low_cardinality_cols),
    "total_df_memory_before_MB": round(mem_before_total / 1e6, 3),
    "total_df_memory_after_MB": round(mem_after_total / 1e6, 3),
    "total_reduction_pct": round((1 - mem_after_total / mem_before_total) * 100, 1),
    "downcast_columns_memory_before_MB": round(mem_before_cols / 1e6, 3),
    "downcast_columns_memory_after_MB": round(mem_after_cols / 1e6, 3),
    "downcast_columns_reduction_pct": round((1 - mem_after_cols / mem_before_cols) * 100, 1),
}
print(f"Whole DataFrame: {mem_before_total/1e6:.3f} MB -> {mem_after_total/1e6:.3f} MB "
      f"({results['pattern_3_category_dtype']['total_reduction_pct']}% reduction)")
print(f"{len(low_cardinality_cols)} downcast columns alone: {mem_before_cols/1e6:.3f} MB -> "
      f"{mem_after_cols/1e6:.3f} MB "
      f"({results['pattern_3_category_dtype']['downcast_columns_reduction_pct']}% reduction)")

# ---------------------------------------------------------------------------
# Pattern 4: groupby-transform instead of merge for a join-back aggregate
print("\n=== Pattern 4: groupby-transform vs merge ===")


def merge_version(data: pd.DataFrame) -> pd.Series:
    agg = data.groupby("Contract", observed=True)["MonthlyCharges"].mean().reset_index()
    agg.columns = ["Contract", "contract_avg_monthly"]
    merged = data.merge(agg, on="Contract", how="left", validate="m:1")
    return merged["contract_avg_monthly"]


def transform_version(data: pd.DataFrame) -> pd.Series:
    return data.groupby("Contract", observed=True)["MonthlyCharges"].transform("mean")


merge_out = merge_version(df).reset_index(drop=True)
transform_out = transform_version(df).reset_index(drop=True)
assert np.allclose(merge_out.values, transform_out.values), "merge and transform must produce identical values"

n_repeat = 20
t_merge = timeit.timeit(lambda: merge_version(df), number=n_repeat) / n_repeat
t_transform = timeit.timeit(lambda: transform_version(df), number=n_repeat) / n_repeat
results["pattern_4_transform_vs_merge"] = {
    "timeit_repeats": n_repeat,
    "merge_seconds": round(t_merge, 6), "transform_seconds": round(t_transform, 6),
    "speedup_x": round(t_merge / t_transform, 2),
    "results_identical": True,
    "note": "transform also avoids the reset_index()/column-rename bookkeeping and cannot silently "
            "change row count the way a badly-validated merge could.",
}
print(f"merge: {t_merge*1000:.3f} ms | groupby.transform: {t_transform*1000:.3f} ms | "
      f"speedup: {t_merge/t_transform:.2f}x (results verified identical)")

import json
(OUT / "pandas_patterns_results.json").write_text(json.dumps(results, indent=2))
print(f"\nResults written to {OUT / 'pandas_patterns_results.json'}")
