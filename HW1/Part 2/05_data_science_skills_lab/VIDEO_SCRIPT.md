Project 05: Data Science Skills Lab

WHAT IT IS
A lab covering 48 different data science skills, demonstrated on real datasets, mainly IBM Telco Customer Churn. The key idea is an independent verification harness: a separate script recomputes every headline number straight from the raw CSV and checks it against what the pipeline claims, so nothing is taken on faith.

HOW TO RUN
Command: make 05   (or ./run --05)
Backend (FastAPI): http://localhost:8005
Frontend (React): http://localhost:5178

FILES TO SHOW ON SCREEN
1. src/verify_claims.py - the independent verification harness
2. src/00_foundation.py - builds the train and test split

CODE - src/verify_claims.py (independent verification)

def check(name, got, want, tol=None, note=""):
    if tol is None:
        ok = got == want
    else:
        ok = want is not None and abs(got - want) <= tol
    checks.append((name, got, want, ok, note))

df = pd.read_csv(RAW)
check("raw sha256", hashlib.sha256(RAW.read_bytes()).hexdigest(), EXPECTED_SHA)
check("row count", len(df), 7043)
check("duplicate customerIDs", int(df.customerID.duplicated().sum()), 0)
check("TotalCharges nulls", int(df.TotalCharges.isna().sum()), 11)

check("logo churn rate %", round(churn.mean() * 100, 3), 26.537, tol=0.001)
check("no train/test ID overlap", len(set(tr.customerID) & set(te.customerID)), 0)

Explain that this file never imports the lab's own pipeline code on purpose. It reads the raw CSV fresh and recalculates every number itself, like the churn rate, the row count, and whether the train and test split leaked any customer IDs. If the pipeline had a bug, importing its code would just reproduce the same bug, so this script deliberately starts from scratch.

SCRIPT

Intro, 0:00 to 0:25
Say you are showing Project 05, the data science skills mastery lab.
Launch it with make 05.
Mention the Makefile checks that the FastAPI backend is running on port 8005 before launching the React client on port 5178.

Code walkthrough, 0:25 to 1:25
Open src/verify_claims.py.
Explain the check function: it compares a freshly computed value against an expected value, with an optional tolerance for floating point numbers.
Point out a few of the actual checks: the raw file's sha256 hash, the row count, duplicate customer IDs, and the churn rate, all recomputed directly from the CSV.
Mention this file deliberately avoids importing the lab's own code, so it cannot accidentally validate a bug against itself. It also checks that the train and test split has zero overlapping customer IDs, ruling out data leakage.
Briefly open src/00_foundation.py and mention this is what builds that stratified train and test split in the first place.

Live demo, 1:25 to 2:15
Switch to the browser at localhost 5178.
Show the 48 skills catalog and run one live.
Open the Telco Churn tab and submit a live prediction, showing the churn probability and risk band.
Point out the other tabs: Titanic classification, Ames Housing regression, and Credit Card Fraud precision-recall curves.

Wrap up
This concludes Project 05.
