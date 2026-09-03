# ==============================================================================
# Multi-Project Workspace Makefile
# Data Mining HW1 - Part 2
# ==============================================================================
# Usage Examples (ALL targets start frontends / web apps - NO model training):
#   make 00             Start Project 00 Web App (Dynamic TODO Next.js App)
#   make 01             Start Project 01 Web App (FastAPI Backend + Vite Frontend)
#   make 02             Start Project 02 Dashboard (Nano LLM Inspector Dashboard)
#   make 03             Start Project 03 Web App (Customer Segmentation Dashboard)
#   make 04             Start Project 04 Web App (Associative Mining Flask Console)
#   make 05             Start Project 05 Web App (Skills Lab Web Application)
#
# Calling with leading dashes:
#   make -- --00        Start Project 00 using --00 flag format
#   make -- --01        Start Project 01 using --01 flag format
#   ./run --00          Helper script wrapper for --XX flags
# ==============================================================================

PYTHON ?= python3

.DEFAULT_GOAL := help

.PHONY: help all 00 01 02 03 04 05 --00 --01 --02 --03 --04 --05 \
        run-00 run-01 run-02 run-03 run-04 run-05 \
        00_dynamic_todo_workspace 01_nyc_taxi_trip_prediction 02_nano_llm_transformer \
        03_customer_segmentation_clustering 04_associative_pattern_mining 05_data_science_skills_lab \
        todo taxi llm transformer clustering association basket skills_lab telco run \
        train-01 train-02 train-03 train-04 train-05

# ------------------------------------------------------------------------------
# HELP / USAGE DISPLAY
# ------------------------------------------------------------------------------
help:
	@echo "======================================================================"
	@echo "                   MULTI-PROJECT WORKSPACE RUNNER                     "
	@echo "======================================================================"
	@echo "Frontend Launch Commands (Direct Web Apps - NO Model Training):"
	@echo "  make 00  (or make -- --00)  Project 00: Dynamic TODO Web App (Next.js)"
	@echo "  make 01  (or make -- --01)  Project 01: NYC Taxi Prediction Web App"
	@echo "  make 02  (or make -- --02)  Project 02: Nano LLM Transformer Admin Dashboard"
	@echo "  make 03  (or make -- --03)  Project 03: Customer Segmentation React Dashboard"
	@echo "  make 04  (or make -- --04)  Project 04: Associative Mining Flask Console"
	@echo "  make 05  (or make -- --05)  Project 05: Data Science Skills Lab Web App"
	@echo ""
	@echo "Additional Workflows:"
	@echo "  make run PROJECT=01         Run specific project frontend via variable"
	@echo "  ./run --00                  Use helper runner script with -- flags"
	@echo "======================================================================"

# ------------------------------------------------------------------------------
# PROJECT TARGETS & ALIASES (FRONTENDS ONLY - NO MODEL TRAINING)
# ------------------------------------------------------------------------------

# Project 00: Dynamic TODO Workspace (Next.js App)
00: run-00
--00: run-00
00_dynamic_todo_workspace: run-00
todo: run-00
run-00:
	@echo "\n>>> Launching Project 00: Dynamic TODO Next.js Web App..."
	cd 00_dynamic_todo_workspace && npm run dev

# Project 01: NYC Taxi Trip Prediction Web App (FastAPI Backend + Vite Frontend)
01: run-01
--01: run-01
01_nyc_taxi_trip_prediction: run-01
taxi: run-01
run-01:
	@echo "\n>>> Launching Project 01: NYC Taxi Trip Prediction Web App..."
	@if ! lsof -i :8000 > /dev/null; then \
		echo "Starting FastAPI backend on http://localhost:8000..."; \
		(cd 01_nyc_taxi_trip_prediction && nohup $(PYTHON) -m uvicorn deployment.backend.main:app --host 0.0.0.0 --port 8000 > /tmp/taxi_backend.log 2>&1 &); \
		for i in $$(seq 1 10); do \
			if curl -s http://localhost:8000/health | grep -q "healthy"; then \
				echo "Backend API is ready!"; \
				break; \
			fi; \
			sleep 1; \
		done; \
	else \
		echo "Backend API is already running on http://localhost:8000"; \
	fi
	cd 01_nyc_taxi_trip_prediction/deployment/frontend && npm run dev

# Project 02: Nano LLM Transformer Dashboard
02: run-02
--02: run-02
02_nano_llm_transformer: run-02
llm: run-02
transformer: run-02
run-02:
	@echo "\n>>> Launching Project 02: Nano LLM Admin Dashboard on http://localhost:8002..."
	cd 02_nano_llm_transformer && $(PYTHON) -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8002 --reload

# Project 03: Customer Segmentation Clustering React Dashboard
03: run-03
--03: run-03
03_customer_segmentation_clustering: run-03
clustering: run-03
run-03:
	@echo "\n>>> Launching Project 03: Customer Segmentation React Dashboard..."
	cd 03_customer_segmentation_clustering/dashboard && npm run dev

# Project 04: Associative Pattern Mining Flask Dashboard
04: run-04
--04: run-04
04_associative_pattern_mining: run-04
association: run-04
basket: run-04
run-04:
	@echo "\n>>> Launching Project 04: Associative Pattern Mining Flask Dashboard on http://localhost:5050..."
	cd 04_associative_pattern_mining && PORT=5050 $(PYTHON) app.py --port 5050

# Project 05: Data Science Skills Lab Web App (FastAPI Backend + Vite Frontend)
05: run-05
--05: run-05
05_data_science_skills_lab: run-05
skills_lab: run-05
telco: run-05
run-05:
	@echo "\n>>> Launching Project 05: Data Science Skills Lab Web App..."
	@if ! lsof -i :8005 > /dev/null; then \
		echo "Starting FastAPI backend on http://127.0.0.1:8005..."; \
		(cd 05_data_science_skills_lab/webapp/server && nohup $(PYTHON) -m uvicorn main:app --host 127.0.0.1 --port 8005 > /tmp/skills_lab_backend.log 2>&1 &); \
		echo "Warming data science pipeline caches..."; \
		for i in $$(seq 1 45); do \
			if curl -s http://127.0.0.1:8005/api/health | grep -q "ready"; then \
				echo "Backend API is ready!"; \
				break; \
			fi; \
			sleep 1; \
		done; \
	else \
		echo "Backend API is already running on http://127.0.0.1:8005"; \
	fi
	cd 05_data_science_skills_lab/webapp/client && npm run dev

# Parameterized Dynamic Runner (e.g. make run PROJECT=01 or PROJECT=--01)
run:
	@CLEAN_PROJ=$$(echo "$(PROJECT)" | sed 's/^--//'); \
	if [ -z "$$CLEAN_PROJ" ]; then \
		echo "Error: Please specify PROJECT, e.g., make run PROJECT=00 or make run PROJECT=--01"; \
		exit 1; \
	fi; \
	$(MAKE) $$CLEAN_PROJ

# Separate optional targets for manual offline training (NOT run by standard targets)
train-01:
	cd 01_nyc_taxi_trip_prediction && $(PYTHON) download_data.py && $(PYTHON) 2_data_understanding.py && $(PYTHON) 3_data_preparation.py && $(PYTHON) 4_modeling.py

train-02:
	cd 02_nano_llm_transformer && $(PYTHON) train.py

train-03:
	cd 03_customer_segmentation_clustering && if [ -d ".venv" ]; then .venv/bin/python run_pipeline.py; else $(PYTHON) run_pipeline.py; fi

train-04:
	cd 04_associative_pattern_mining && $(PYTHON) run_pipeline.py

train-05:
	cd 05_data_science_skills_lab && $(PYTHON) src/00_foundation.py && $(PYTHON) src/verify_claims.py
