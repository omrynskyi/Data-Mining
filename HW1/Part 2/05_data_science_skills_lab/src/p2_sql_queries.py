"""
Phase 2 - Data Understanding: real business SQL run against artifacts/telco.db.

Two queries, written for a retention team building a monthly risk list:
  1. churn_rate_by_contract  — churn rate and volume broken down by contract type.
  2. revenue_at_risk_by_contract — for currently-active customers, MRR by contract
     type weighted by that contract type's historical churn rate, i.e. the monthly
     revenue expected to be lost to churn if historical rates hold. This is the
     number query-validation and sql-to-business-logic are exercised against.

Saves the .sql text and the executed result sets so both downstream skills work
against the exact same, real query.
"""
import pathlib
import sqlite3

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_OUT = ROOT / "artifacts" / "sql"
SQL_OUT.mkdir(parents=True, exist_ok=True)
db_path = ROOT / "artifacts" / "telco.db"

CHURN_RATE_BY_CONTRACT = """\
SELECT
    Contract,
    COUNT(*) AS n_customers,
    SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) AS churn_rate_pct
FROM customers
GROUP BY Contract
ORDER BY churn_rate_pct DESC;
"""

REVENUE_AT_RISK_BY_CONTRACT = """\
SELECT
    c1.Contract,
    COUNT(*) AS n_active_customers,
    ROUND(SUM(c1.MonthlyCharges), 2) AS active_mrr,
    ROUND(
        (SELECT 1.0 * SUM(CASE WHEN c2.Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)
         FROM customers c2 WHERE c2.Contract = c1.Contract),
        4
    ) AS historical_churn_rate,
    ROUND(
        SUM(c1.MonthlyCharges) *
        (SELECT 1.0 * SUM(CASE WHEN c2.Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)
         FROM customers c2 WHERE c2.Contract = c1.Contract),
        2
    ) AS expected_monthly_revenue_at_risk
FROM customers c1
WHERE c1.Churn = 'No'
GROUP BY c1.Contract
ORDER BY expected_monthly_revenue_at_risk DESC;
"""

(SQL_OUT / "churn_rate_by_contract.sql").write_text(CHURN_RATE_BY_CONTRACT)
(SQL_OUT / "revenue_at_risk_by_contract.sql").write_text(REVENUE_AT_RISK_BY_CONTRACT)

conn = sqlite3.connect(db_path)

df1 = pd.read_sql_query(CHURN_RATE_BY_CONTRACT, conn)
df1.to_csv(SQL_OUT / "churn_rate_by_contract_result.csv", index=False)
print("=== churn_rate_by_contract ===")
print(df1.to_string(index=False))

df2 = pd.read_sql_query(REVENUE_AT_RISK_BY_CONTRACT, conn)
df2.to_csv(SQL_OUT / "revenue_at_risk_by_contract_result.csv", index=False)
print("\n=== revenue_at_risk_by_contract ===")
print(df2.to_string(index=False))

total_at_risk = df2["expected_monthly_revenue_at_risk"].sum()
total_active_mrr = df2["active_mrr"].sum()
print(f"\nTotal active MRR: ${total_active_mrr:,.2f}  |  "
      f"Total expected monthly revenue at risk: ${total_at_risk:,.2f} "
      f"({total_at_risk/total_active_mrr:.1%} of active MRR)")

# EXPLAIN QUERY PLAN for both — feeds query-validation
for name, sql in [("churn_rate_by_contract", CHURN_RATE_BY_CONTRACT),
                   ("revenue_at_risk_by_contract", REVENUE_AT_RISK_BY_CONTRACT)]:
    plan = pd.read_sql_query(f"EXPLAIN QUERY PLAN {sql}", conn)
    plan.to_csv(SQL_OUT / f"{name}_explain_plan.csv", index=False)
    print(f"\n=== EXPLAIN QUERY PLAN: {name} ===")
    print(plan.to_string(index=False))

conn.close()
