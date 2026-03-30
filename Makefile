# ============================================================
# South Shore Sentiment Study — Task Runner
# ============================================================
.PHONY: help install init-db ingest ingest-synthetic clean-data analyze \
        dashboard report excel-report pg-load run-all test lint format pre-commit-fix

PYTHON = python
STREAMLIT = streamlit

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and package in editable mode
	pip install -r requirements.txt
	pip install -e .
	$(PYTHON) -m spacy download en_core_web_sm
	@echo "✅ Dependencies installed and package configured"

init-db: ## Initialize DuckDB database
	$(PYTHON) -c "from src.utils.db import init_database; init_database()"
	@echo "✅ Database initialized"

ingest: ## Collect data from Reddit + News + YouTube
	$(PYTHON) -m src.ingestion.pipeline --mode live
	@echo "✅ Data ingestion complete"

ingest-synthetic: ## Generate synthetic fallback data
	$(PYTHON) -m src.ingestion.pipeline --mode synthetic
	@echo "✅ Synthetic data generated"

clean-data: ## Run text cleaning pipeline
	$(PYTHON) -m src.analysis.cleaning
	@echo "✅ Data cleaning complete"

analyze: ## Run full analysis (sentiment + emotion + topics + geo + longitudinal)
	$(PYTHON) -m src.analysis.sentiment
	$(PYTHON) -m src.analysis.emotions
	$(PYTHON) -m src.analysis.topics
	$(PYTHON) -m src.analysis.geo_tagger
	$(PYTHON) -m src.analysis.phase_tagger
	$(PYTHON) -m src.analysis.longitudinal
	@echo "✅ Analysis complete"

dashboard: ## Launch Streamlit dashboard
	$(STREAMLIT) run dashboards/app.py --server.port 8501

report: ## Generate PDF report
	$(PYTHON) -m src.visualization.report_generator
	@echo "✅ PDF report generated"

excel-report: ## Generate Excel workbook with KPIs and charts
	$(PYTHON) -m src.exports.excel_report
	@echo "✅ Excel report generated in reports/"

pg-load: ## Load analyzed data into PostgreSQL star schema
	$(PYTHON) -m src.utils.postgres_loader
	@echo "✅ PostgreSQL loaded"

run-all: init-db ingest-synthetic clean-data analyze report excel-report ## Run full pipeline end-to-end
	@echo "🎉 Full pipeline complete"

test: ## Run test suite
	$(PYTHON) -m pytest tests/ -v --cov=src

lint: ## Code quality checks
	ruff check src/ tests/ dashboards/
	ruff format --check src/ tests/ dashboards/

format: ## Auto-format code
	ruff format src/ tests/ dashboards/
	ruff check --fix src/ tests/ dashboards/

pre-commit-fix: format ## Format and lint before committing
	@echo "✅ Code formatted. Ready to commit."
