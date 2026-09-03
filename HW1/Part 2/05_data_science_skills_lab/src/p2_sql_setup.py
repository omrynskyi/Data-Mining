"""
Phase 2 - Data Understanding: builds artifacts/telco.db (SQLite), the real database
that query-validation, sql-to-business-logic, and metric-reconciliation are run against.

Loads the raw CSV as-is into a `customers_raw` table (TotalCharges stays TEXT, exactly
as shipped, including the 11 blank strings) plus a cleaned `customers` view with
TotalCharges cast to REAL, so SQL work can demonstrate handling the real messiness.
"""
import pathlib
import sqlite3

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
db_path = ROOT / "artifacts" / "telco.db"
db_path.unlink(missing_ok=True)

raw = ROOT / "data" / "Telco-Customer-Churn.csv"
df = pd.read_csv(raw, dtype={"TotalCharges": str})

conn = sqlite3.connect(db_path)
df.to_sql("customers_raw", conn, index=False, if_exists="replace")

conn.execute("""
CREATE VIEW customers AS
SELECT
    customerID,
    gender,
    SeniorCitizen,
    Partner,
    Dependents,
    tenure,
    PhoneService,
    MultipleLines,
    InternetService,
    OnlineSecurity,
    OnlineBackup,
    DeviceProtection,
    TechSupport,
    StreamingTV,
    StreamingMovies,
    Contract,
    PaperlessBilling,
    PaymentMethod,
    MonthlyCharges,
    CASE WHEN TRIM(TotalCharges) = '' THEN NULL ELSE CAST(TotalCharges AS REAL) END AS TotalCharges,
    Churn
FROM customers_raw;
""")
conn.execute("CREATE INDEX idx_customers_raw_id ON customers_raw(customerID);")
conn.commit()

n_raw = conn.execute("SELECT COUNT(*) FROM customers_raw").fetchone()[0]
n_view = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
n_null_tc = conn.execute("SELECT COUNT(*) FROM customers WHERE TotalCharges IS NULL").fetchone()[0]
print(f"Loaded {n_raw} rows into customers_raw, view customers exposes {n_view} rows, "
      f"{n_null_tc} with NULL TotalCharges.")
conn.close()
print(f"DB written to {db_path}")
