# Original User Request

## 2026-09-02T17:25:55Z

Perform associative pattern mining on a popular Kaggle dataset following the CRISP-DM framework. The project must include automated research (hill climbing) to match results with a selected research paper, and provide a comprehensive data science admin dashboard tailored for data scientists and AI engineers.

Working directory: ~/teamwork_projects/associative_pattern_mining
Integrity mode: development

## Requirements

### R1. CRISP-DM Implementation & Data Processing
The team must implement a data pipeline following the CRISP-DM framework, using a self-selected popular associative pattern mining dataset from Kaggle. The pipeline should handle data understanding, preparation, and modeling.

### R2. Automated Research & Hill Climbing
The team must autonomously search for a relevant research paper on associative pattern mining and implement an automated hill-climbing optimization process to match or approximate the paper's reported metrics or findings.

### R3. Data Science Admin Dashboard
The team must build a comprehensive dashboard designed for data scientists and AI engineers. It should visualize the CRISP-DM phases, the discovered association rules, and the results of the hill-climbing optimization against the target research paper.

## Acceptance Criteria

### CRISP-DM Pipeline (R1)
- [ ] A `run_pipeline.py` script executes successfully end-to-end without manual intervention.
- [ ] The pipeline outputs a summary artifact detailing the data preparation steps and the top discovered association rules.

### Optimization Search (R2)
- [ ] A `run_optimization.py` script executes the hill-climbing search without errors.
- [ ] The output log identifies the target research paper and shows the progression of evaluation metrics over multiple iterations.

### Dashboard (R3)
- [ ] The dashboard application starts cleanly via a single command (e.g., `python app.py`) and serves on a local port returning a 200 OK status.
- [ ] The dashboard UI contains clear sections dedicated to the CRISP-DM process, the hill-climbing results, and rule visualization.
