BACKEND  := backend
FRONTEND := frontend
UV       := uv --directory $(BACKEND)
# Extra ruff options; CI passes --output-format=github for inline PR annotations.
RUFF_ARGS ?=

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
	test lint lint-backend lint-rules-backend format-check-backend format \
	typecheck typecheck-backend typecheck-frontend build-frontend \
	check check-backend check-frontend check-repo clean

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-22s %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install exact locked dependencies (uv.lock, package-lock.json)

install-backend: ## Install backend dependencies from uv.lock, failing if it is stale
	$(UV) sync --locked

install-frontend: ## Install frontend dependencies from package-lock.json
	npm --prefix $(FRONTEND) ci

dev: ## Run backend (:8000) and frontend (:5173) together
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	$(UV) run uvicorn app.main:create_app --factory --reload --port 8000

dev-frontend:
	npm --prefix $(FRONTEND) run dev

test: ## Run the backend test suite (mock mode, no network)
	MOCK_LLM=1 $(UV) run pytest

lint: lint-backend ## Lint (readability rules, D042) and check formatting

lint-backend: lint-rules-backend format-check-backend

lint-rules-backend: ## Readability and cleanliness rules (complexity, unused code, naive datetimes...)
	$(UV) run ruff check . $(RUFF_ARGS)

format-check-backend: ## Fail if any file is not ruff-formatted
	$(UV) run ruff format --check .

format: ## Auto-format backend code
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck: typecheck-backend typecheck-frontend ## Type-check backend (mypy) and frontend (tsc)

typecheck-backend:
	$(UV) run mypy app tests

typecheck-frontend:
	npm --prefix $(FRONTEND) run typecheck

build-frontend: ## Type-check and build the frontend bundle
	npm --prefix $(FRONTEND) run build

check-backend: lint-backend typecheck-backend test ## Backend checks, as run by CI

check-frontend: build-frontend ## Frontend checks, as run by CI (build includes tsc)

check-repo: ## Fail if a secret or database file is tracked by git (rule 7)
	@tracked="$$(git ls-files | grep -E '(^|/)\.env(\..+)?$$|\.(db|sqlite3?)$$' | grep -v '\.env\.example$$' || true)"; \
	if [ -n "$$tracked" ]; then echo "Tracked files that must never be committed:"; echo "$$tracked"; exit 1; fi; \
	echo "No .env or database files are tracked."

check: check-repo check-backend check-frontend ## Everything CI runs

clean: ## Remove caches and build output
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache $(FRONTEND)/dist
