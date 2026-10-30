PYTHON ?= .venv/Scripts/python.exe
STREAMLIT ?= .venv/Scripts/streamlit.exe
DATA_DIR ?= data

.PHONY: help install generate validate validate-scenarios validate-baseline analyze check-acks inspect build-db test dashboard clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

generate: ## Regenerate dataset + analysis + validators
	$(PYTHON) src/pipeline.py --with-analysis

validate: ## Run the baseline data validator
	$(PYTHON) src/validate_data.py

validate-baseline: validate

validate-scenarios: ## Run the edge-case / detector validator
	$(PYTHON) src/validate_edge_cases.py

analyze: ## Recompute analytical outputs (no regeneration)
	$(PYTHON) src/safety_analyzer.py

check-acks: ## Print activation-denominated acknowledgement statistics
	$(PYTHON) src/check_ack_stats.py

inspect: ## Inspect committed CSV schemas and dtypes
	$(PYTHON) src/inspect_schema.py

build-db: ## Build the SQLite export
	$(PYTHON) src/build_database.py

test: ## Run the pytest suite
	$(PYTHON) -m pytest tests -q

dashboard: ## Launch the Streamlit dashboard
	$(STREAMLIT) run dashboard/app.py --server.headless true

clean:
	rm -rf .pytest_cache .ruff_cache data/cache data/exports data/industrial_safety.db
