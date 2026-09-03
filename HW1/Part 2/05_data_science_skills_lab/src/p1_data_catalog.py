"""CRISP-DM Phase 1 - data-catalog-entry skill applied to Telco churn.

Extracts real technical metadata (dtype, cardinality, null count, example values)
for all 21 columns of data/Telco-Customer-Churn.csv, in the spirit of
.claude/skills/data-catalog-entry/scripts/catalog_extractor.py (that script targets
a live SQL database via SQLAlchemy inspection; this is the flat-file equivalent for
a CSV source, following the same technical-metadata-extraction step of the skill's
process). Business definitions are added by hand (the skill's "collect business
context" step, simulated here per the team-lead brief's business framing).

Outputs:
  artifacts/data_catalog_telco.json
  artifacts/data_catalog_telco.md
"""
import json
import pathlib
from datetime import datetime, timezone

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "Telco-Customer-Churn.csv"
OUT_JSON = ROOT / "artifacts" / "data_catalog_telco.json"
OUT_MD = ROOT / "artifacts" / "data_catalog_telco.md"

df = pd.read_csv(RAW)
extracted_at = datetime.now(timezone.utc).isoformat()

# Business definitions (simulated data-owner interview - see business-metrics-calculator
# and stakeholder-requirements-gathering docs for the same simulated stakeholder).
BUSINESS_DEFS = {
    "customerID": "Unique customer identifier assigned at account creation. Primary key.",
    "gender": "Customer's self-reported gender at signup (Male/Female, as captured by this legacy system).",
    "SeniorCitizen": "Whether the account holder is 65+ (1) or not (0), self-reported at signup.",
    "Partner": "Whether the customer has a partner (spouse/domestic partner) on the account profile.",
    "Dependents": "Whether the customer has dependents (children/other dependents) on the account profile.",
    "tenure": "Number of months the customer has been with the company as of the snapshot date. Used as the acquisition-to-date clock (business framing: months since acquisition).",
    "PhoneService": "Whether the customer subscribes to the phone service line.",
    "MultipleLines": "Whether the customer has multiple phone lines (No / Yes / No phone service).",
    "InternetService": "Internet service technology subscribed to (DSL / Fiber optic / No internet service).",
    "OnlineSecurity": "Whether the customer subscribes to the online security add-on (requires internet service).",
    "OnlineBackup": "Whether the customer subscribes to the online backup add-on (requires internet service).",
    "DeviceProtection": "Whether the customer subscribes to the device protection add-on (requires internet service).",
    "TechSupport": "Whether the customer subscribes to the tech support add-on (requires internet service).",
    "StreamingTV": "Whether the customer subscribes to the streaming TV add-on (requires internet service).",
    "StreamingMovies": "Whether the customer subscribes to the streaming movies add-on (requires internet service).",
    "Contract": "Contract commitment term: Month-to-month, One year, or Two year. Primary churn-risk driver dimension.",
    "PaperlessBilling": "Whether the customer is enrolled in paperless billing (Yes/No).",
    "PaymentMethod": "How the customer pays their bill (Electronic check, Mailed check, Bank transfer (automatic), Credit card (automatic)).",
    "MonthlyCharges": "Current recurring monthly charge in USD - treated as the customer's MRR contribution (business framing).",
    "TotalCharges": "Cumulative amount billed to the customer to date (USD). Approximately tenure x MonthlyCharges, with small deviations from mid-cycle rate changes; blank for 11 customers with tenure=0 (billed nothing yet).",
    "Churn": "Target label: whether the customer churned (voluntarily left) during the observation window (Yes/No).",
}

CRITICALITY = {
    "customerID": "critical", "tenure": "critical", "Contract": "critical",
    "MonthlyCharges": "critical", "TotalCharges": "critical", "Churn": "critical",
    "InternetService": "high", "PaymentMethod": "high", "PaperlessBilling": "medium",
}

def profile_column(col: str) -> dict:
    s = df[col]
    dtype = str(s.dtype)
    n_nulls = int(s.isna().sum())
    n_unique = int(s.nunique(dropna=True))
    examples = [x for x in s.dropna().unique()[:5].tolist()]
    # special-case TotalCharges: raw dtype is object due to blank strings
    numeric_note = None
    if col == "TotalCharges":
        coerced = pd.to_numeric(s.str.strip(), errors="coerce")
        n_nulls = int(coerced.isna().sum())
        numeric_note = (
            f"Ships as object dtype (blank strings for tenure=0 rows); "
            f"{n_nulls} rows become null after pd.to_numeric coercion (see data/processed/dataset_meta.json)."
        )
    return {
        "name": col,
        "dtype_raw": dtype,
        "nullable": n_nulls > 0,
        "null_count": n_nulls,
        "null_pct": round(n_nulls / len(df) * 100, 3),
        "cardinality": n_unique,
        "is_categorical_low_cardinality": n_unique <= 10 and dtype == "object",
        "example_values": examples,
        "business_definition": BUSINESS_DEFS.get(col, ""),
        "criticality": CRITICALITY.get(col, "medium"),
        "primary_key": col == "customerID",
        "notes": numeric_note,
    }

columns = [profile_column(c) for c in df.columns]

catalog = {
    "table_name": "Telco-Customer-Churn",
    "qualified_name": "data/Telco-Customer-Churn.csv",
    "domain": "Customer / Subscription (Telecom)",
    "criticality": "critical",
    "description": "One row per residential telecom customer, capturing subscribed "
                    "services, account/contract attributes, billing amounts, and whether "
                    "the customer churned. Source: Kaggle blastchar/telco-customer-churn "
                    "(IBM Telco Customer Churn sample dataset).",
    "grain": "One row per customer (customerID), snapshot at time of extract.",
    "row_count": len(df),
    "column_count": df.shape[1],
    "extracted_at": extracted_at,
    "primary_key": "customerID",
    "duplicate_customer_ids": int(df["customerID"].duplicated().sum()),
    "business_owner": "[simulated stakeholder input] VP of Customer Retention",
    "technical_owner": "[simulated stakeholder input] Data Science / Analytics team (this project)",
    "upstream_sources": ["Kaggle dataset export (static, one-time download for this lab); "
                          "in production this would be the billing system + CRM."],
    "downstream_consumers": ["CRISP-DM churn-prediction pipeline (this project, phases 2-6)",
                              "Retention team ranked risk list (planned deliverable)"],
    "access_level": "internal",
    "sensitivity": "PII (customerID is a pseudonymous key; gender, SeniorCitizen are "
                    "demographic attributes) + billing/financial (MonthlyCharges, TotalCharges)",
    "compliance_tags": ["none applicable - public Kaggle sample; would be PII/financial "
                         "in a real production telecom system"],
    "columns": columns,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(catalog, indent=2, default=str))

# --- Markdown rendering, following catalog_entry_template.md structure ---------
md_lines = [
    f"# {catalog['table_name']}",
    "",
    "## Overview",
    "",
    f"**Name:** `{catalog['qualified_name']}`  ",
    "**Type:** flat file (CSV) — modeled as a table  ",
    f"**Domain:** {catalog['domain']}  ",
    f"**Criticality:** {catalog['criticality']}  ",
    "",
    "**Description:**  ",
    catalog["description"],
    "",
    f"**Grain:** {catalog['grain']}",
    "",
    "---",
    "",
    "## Ownership",
    "",
    f"- **Business Owner:** {catalog['business_owner']}",
    f"- **Technical Owner:** {catalog['technical_owner']}",
    f"- **Last reviewed:** {extracted_at[:10]}",
    "",
    "---",
    "",
    "## Schema",
    "",
    f"**Row Count (at extraction):** {catalog['row_count']:,}  ",
    f"**Column Count:** {catalog['column_count']}  ",
    f"**Extracted:** {extracted_at}  ",
    f"**Duplicate customerIDs:** {catalog['duplicate_customer_ids']}",
    "",
    "| Column | Dtype (raw) | Nullable | Null % | Cardinality | Example values | Business definition |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
for c in columns:
    examples = ", ".join(str(e) for e in c["example_values"])
    key = "PK" if c["primary_key"] else "—"
    md_lines.append(
        f"| {c['name']} | {c['dtype_raw']} | {'Yes' if c['nullable'] else 'No'} "
        f"({c['null_pct']}%) | {key} | {c['cardinality']} | {examples} | {c['business_definition']} |"
    )

md_lines += [
    "",
    "### Notes on individual columns",
    "",
]
for c in columns:
    if c["notes"]:
        md_lines.append(f"- **{c['name']}:** {c['notes']}")

md_lines += [
    "",
    "---",
    "",
    "## Relationships",
    "",
    f"**Primary key:** `{catalog['primary_key']}` (0 duplicates confirmed)",
    "",
    "**Foreign keys:** none — single flat table.",
    "",
    "---",
    "",
    "## Data Quality",
    "",
    f"- **Completeness:** 100% for 20/21 columns; `TotalCharges` has 11 nulls "
    f"({11/len(df)*100:.2f}%) after numeric coercion, all corresponding to "
    "`tenure == 0` (brand-new customers who have not yet been billed) — expected, not a defect.",
    "- **Freshness:** static snapshot (one-time Kaggle download for this lab); "
    "no refresh schedule.",
    "- **Known issues:** `TotalCharges` ships as `object` dtype due to blank-string "
    "placeholders and must be coerced with `pd.to_numeric(..., errors='coerce')` "
    "before numeric use (see `src/00_foundation.py`).",
    "",
    "---",
    "",
    "## Lineage",
    "",
    "**Upstream sources:**",
]
for s in catalog["upstream_sources"]:
    md_lines.append(f"- {s}")
md_lines += ["", "**Downstream consumers:**"]
for s in catalog["downstream_consumers"]:
    md_lines.append(f"- {s}")

md_lines += [
    "",
    "---",
    "",
    "## Access & Governance",
    "",
    f"**Access level:** {catalog['access_level']}  ",
    f"**Sensitivity:** {catalog['sensitivity']}  ",
    f"**Compliance tags:** {', '.join(catalog['compliance_tags'])}  ",
    "",
    "**Access instructions:**  ",
    "Public Kaggle dataset — no access request needed for this lab. In a production "
    "system this would sit behind the standard customer-data access request process.",
    "",
    "---",
    "",
    "## Sample query",
    "",
    "```python",
    "import pandas as pd",
    "df = pd.read_csv('data/Telco-Customer-Churn.csv')",
    "df.head(10)",
    "```",
    "",
    "---",
    "",
    f"*Generated by `src/p1_data_catalog.py` on {extracted_at}. "
    "Template: data-catalog-entry/assets/catalog_entry_template.md*",
]

OUT_MD.write_text("\n".join(md_lines))
print(f"Wrote {OUT_JSON}")
print(f"Wrote {OUT_MD}")
print(f"Columns profiled: {len(columns)}")
