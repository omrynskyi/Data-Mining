# Data Science Skills Mastery Lab — Web App

An interactive skills-catalog web app for the 48 agent skills demonstrated in this project,
modeled on a reference implementation, rebuilt here with **real downloaded data throughout** —
no client-side simulation, no synthesized "Kaggle" data.

## What's real

| Tab | Dataset | Real, verified fact |
|---|---|---|
| Titanic | `webapp/data/titanic.csv` — real Kaggle-equivalent Titanic (891 rows) | 38.38% survival rate |
| House Prices | `webapp/data/AmesHousing.txt` — the real Ames Housing dataset (2,930 rows) Kaggle's competition is built from | Dean De Cock's official source |
| Fraud | `webapp/data/creditcard.csv` — the real ULB Credit Card Fraud dataset (284,807 rows) | 0.1727% fraud rate — matches the published real statistic exactly |
| E-Commerce | `webapp/data/online_retail.xlsx` — real UCI Online Retail transactions (~541,909 rows) | genuinely messy: real missing CustomerIDs, real returns, real cancellations |
| Telco Churn | bridges into this project's own already-completed, 48-skill CRISP-DM lab | live predictions from the actual trained, calibrated model (`../artifacts/model.joblib`) |

## Quick start

```bash
# Backend (FastAPI on port 8005)
cd webapp/server
python3 -m uvicorn main:app --host 127.0.0.1 --port 8005

# Frontend (Vite + React on port 5178)
cd webapp/client
npm install
npm run dev   # open http://localhost:5178/
```

## Layout

```
webapp/
├── data/      real downloaded CSV/XLSX source files (not committed data pretending to be real)
├── core/      dataset loaders + real sklearn/analytics pipelines, computed once and cached
├── server/    FastAPI app (server/main.py) + live API smoke test transcript
└── client/    Vite + React frontend
```
