# Project Execution Plan: Customer Segmentation & Dashboard

## Overview
Build an end-to-end CRISP-DM Mall Customer Segmentation pipeline (`run_pipeline.py`), an autoresearch hill climbing optimization script aligned to an academic benchmark paper (`optimization_log.md`), and a React Data Science Admin Dashboard with rendering tests.

## Phases
1. **Phase 0: Survey & Specification**
   - Survey 1: Investigate current workspace, dataset files, dependencies, Python & Node environment.
   - Survey 2: Academic paper & clustering benchmark analysis (extracting metrics, methodology, baseline paper targets for Mall Customers dataset).
   - Survey 3: React dashboard requirements, chart libraries, architecture, data contracts.
   - Output: `PROJECT.md` with Feature Inventory, Architecture, Milestones, and Interface Contracts.

2. **Phase 1: Dual Track Launch**
   - **Track A: E2E Testing Track**
     - Design comprehensive opaque-box test suite (Tiers 1-4).
     - Test infrastructure for pipeline execution, dashboard build & render, autoresearch output validation.
     - Publishes `TEST_READY.md`.
   - **Track B: Implementation Track**
     - **Milestone 1**: CRISP-DM Machine Learning Pipeline
       - Business & Data Understanding, Data Prep, Feature Engineering.
       - Clustering algorithms (K-Means, DBSCAN, Agglomerative/GMM if appropriate).
       - Evaluation metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz, Inertia).
       - `run_pipeline.py` emitting models, cluster labels, evaluation JSON/CSV artifacts.
     - **Milestone 2**: Autoresearch & Hill Climbing Optimization
       - Benchmark paper metric extraction & citation.
       - Hill climbing hyperparameter search across feature subsets, scalers, algorithm parameters (k, eps, min_samples, linkage).
       - Generates `optimization_log.md` detailing iterations, baseline vs tuned metrics.
     - **Milestone 3**: React Data Science Admin Dashboard
       - React frontend (Vite/CRA/Next as appropriate, Lucide/Tailwind/Recharts or Chart.js).
       - Visualizations: 2D/3D cluster scatter plots, feature distributions (Age, Income, Spending Score), KPIs, customer persona cards.
       - Connects to pipeline output artifacts / export JSON.
       - `npm run build` passing cleanly.
       - Programmatic render test (Jest / React Testing Library / Puppeteer / Vitest) verifying main components and charts render.

3. **Phase 2: Final Verification & Adversarial Hardening**
   - Verification against 100% E2E test suite.
   - Tier 5 adversarial testing & edge case validation.
   - Forensic integrity audit (`teamwork_preview_auditor`).
   - Final completion reporting.
