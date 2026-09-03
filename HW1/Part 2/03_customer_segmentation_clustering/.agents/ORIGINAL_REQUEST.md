# Original User Request

## 2026-09-02T17:21:51Z

# Teamwork Project Prompt — Draft

> Status: Ready for launch — awaiting user approval
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full agent team

Perform customer clustering on the Mall Customer Segmentation dataset following the CRISP-DM framework. The project includes building a React-based data science admin dashboard and implementing an 'autoresearch' process using hill climbing to align the clustering methodology and dashboard details with a relevant research paper.

Working directory: ~/teamwork_projects/customer_clustering_dashboard
Integrity mode: development

## Requirements

### R1. CRISP-DM & Clustering Pipeline
Implement an end-to-end machine learning pipeline for the Mall Customer Segmentation dataset following the CRISP-DM framework. This must include automated scripts for data preparation, clustering (e.g., K-Means, DBSCAN), and evaluation.

### R2. React Data Science Dashboard
Develop a data science admin dashboard using React to visualize the customer segments, key performance indicators, and data distributions. It should connect to the outputs of the clustering pipeline.

### R3. Autoresearch & Hill Climbing Alignment
Create an automated research script that identifies a benchmark academic paper on customer segmentation, extracts its evaluation metrics, and uses a hill-climbing optimization approach to iteratively tune the clustering hyperparameters to approach or match the paper's results.

## Acceptance Criteria

### Pipeline Execution
- [ ] Running `python run_pipeline.py` executes successfully, processes the dataset, and outputs evaluation metrics (e.g., Silhouette score) and model artifacts to a defined directory.

### Dashboard Build & Render
- [ ] Running `npm run build` inside the dashboard directory completes without errors.
- [ ] A programmatic test (e.g., using Jest or Puppeteer) verifies that the main dashboard components and charts render successfully.

### Autoresearch Verification
- [ ] The autoresearch script generates an `optimization_log.md` file that explicitly cites the benchmark research paper, lists the baseline metrics, and records the iterative steps and metric improvements achieved via hill climbing.
