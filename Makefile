BACKEND  := backend
FRONTEND := frontend
UV       := uv --directory $(BACKEND)

.PHONY: help install dev dev-backend dev-frontend test lint format typecheck check clean

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install exact locked dependencies (uv.lock, package-lock.json)
	$(UV) sync --locked
	npm --prefix $(FRONTEND) ci

dev: ## Run backend (:8000) and frontend (:5173) together
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	$(UV) run uvicorn app.main:create_app --factory --reload --port 8000

dev-frontend:
	npm --prefix $(FRONTEND) run dev

test: ## Run the backend test suite (mock mode, no network)
	MOCK_LLM=1 $(UV) run pytest

lint: ## Lint and check formatting
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Auto-format backend code
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck: ## Type-check backend (mypy) and frontend (tsc)
	$(UV) run mypy app tests
	npm --prefix $(FRONTEND) run typecheck

check: lint typecheck test ## Everything CI would run

clean: ## Remove caches and build output
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache $(FRONTEND)/dist
