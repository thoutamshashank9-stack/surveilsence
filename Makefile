.PHONY: help install dev test lint format clean backend frontend models

# ============================================
# Edge AI CCTV Analytics Platform — Makefile
# ============================================

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------- Setup ----------

install: ## Install all dependencies (backend + frontend)
	cd backend && pip install -r requirements/base.txt -r requirements/dev.txt -r requirements/inference.txt
	cd frontend && npm install

models: ## Download AI models
	python scripts/model_downloader.py

# ---------- Development ----------

backend: ## Start backend dev server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev: ## Start both backend and frontend (requires separate terminals)
	@echo "Run 'make backend' in one terminal and 'make frontend' in another"

# ---------- Testing ----------

test: ## Run all tests
	cd backend && python -m pytest tests/ -v

test-unit: ## Run unit tests only
	cd backend && python -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	cd backend && python -m pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html

# ---------- Code Quality ----------

lint: ## Run linter
	cd backend && python -m ruff check app/ tests/

format: ## Format code
	cd backend && python -m ruff format app/ tests/
	cd backend && python -m ruff check --fix app/ tests/

typecheck: ## Run type checker
	cd backend && python -m mypy app/

# ---------- Database ----------

db-migrate: ## Create new migration
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply migrations
	cd backend && alembic upgrade head

db-downgrade: ## Rollback last migration
	cd backend && alembic downgrade -1

# ---------- Cleanup ----------

clean: ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage
	rm -rf frontend/dist frontend/node_modules/.cache
