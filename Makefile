BACKEND  := backend
FRONTEND := frontend
UV       := uv --directory $(BACKEND)
PLANNER  := planner
UVP      := uv --directory $(PLANNER)
# Extra ruff options; CI passes --output-format=github for inline PR annotations.
RUFF_ARGS ?=
# Backend port for `make dev`; the frontend proxy follows it (make dev BACKEND_PORT=8001).
BACKEND_PORT ?= 8000

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
	seed user record-demo test lint lint-backend lint-rules-backend format-check-backend format \
	typecheck typecheck-backend typecheck-frontend build-frontend lint-frontend test-frontend \
	check check-backend check-frontend check-repo preflight clean \
	install-planner check-planner planner planner-site

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-22s %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install exact locked dependencies (uv.lock, package-lock.json)

install-backend: ## Install backend dependencies from uv.lock, failing if it is stale
	$(UV) sync --locked

install-frontend: ## Install frontend dependencies from package-lock.json
	npm --prefix $(FRONTEND) ci

dev: ## Run backend (BACKEND_PORT, default 8000) and frontend (:5173) together
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	$(UV) run uvicorn app.main:create_app --factory --reload --port $(BACKEND_PORT)

dev-frontend:
	FIELDPILOT_API_TARGET=http://localhost:$(BACKEND_PORT) npm --prefix $(FRONTEND) run dev

seed: ## Rebuild the demo farm (fresh DB, maize cycle; stop `make dev` first)
	$(UV) run python scripts/seed_demo.py --force

user: ## Create an account of any role on this server (PHONE= NAME= ROLE= [PLOTS="1 2"]; D082)
	$(UV) run python scripts/create_user.py --phone "$(PHONE)" --name "$(NAME)" --role "$(ROLE)" \
		$(foreach p,$(PLOTS),--plot $(p))

record-demo: ## Record the two-day demo against the real model (network, key quota; not in CI, D076)
	MOCK_LLM=0 $(UV) run python scripts/record_demo.py

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
	$(UV) run mypy app tests scripts

typecheck-frontend:
	npm --prefix $(FRONTEND) run typecheck

build-frontend: ## Type-check and build the frontend bundle
	npm --prefix $(FRONTEND) run build

check-backend: lint-backend typecheck-backend test ## Backend checks, as run by CI

lint-frontend: ## Oxlint: correctness, suspicious code and the React hooks rules (D068, D069)
	npm --prefix $(FRONTEND) run lint

test-frontend: ## Vitest unit tests of the frontend's pure logic (D068)
	npm --prefix $(FRONTEND) test

check-frontend: lint-frontend test-frontend build-frontend ## Frontend checks, as run by CI (build includes tsc)

check-repo: ## Fail if a secret, database file or database backup is tracked by git (rule 7)
	@tracked="$$(git ls-files | grep -E '(^|/)\.env(\..+)?$$|\.(db|sqlite3?)([.-].+)?$$' | grep -v '\.env\.example$$' || true)"; \
	if [ -n "$$tracked" ]; then echo "Tracked files that must never be committed:"; echo "$$tracked"; exit 1; fi; \
	echo "No .env or database files are tracked."

install-planner: ## Install the planner's checks (no torch: training runs on the GPU machine, D079)
	$(UVP) sync --locked

check-planner: ## Planner checks, as run by CI: ruff, mypy, pytest (no network, no GPU)
	$(UVP) run ruff check . $(RUFF_ARGS)
	$(UVP) run ruff format --check .
	$(UVP) run mypy fieldpilot_planner tests
	$(UVP) run pytest

planner: ## Run planner stages here (STAGES="clean labels"); Windows uses planner/train_windows.ps1
	$(UVP) sync --locked --extra data --extra train
	$(UVP) run python -m fieldpilot_planner $(or $(STAGES),all)

planner-site: ## Snapshot a plot's soil, climate and ONI for the planner (PLOT= LAT= LON= [ELEV=]; network, D081)
	$(UVP) run --extra data python -m fieldpilot_planner.site --lat $(LAT) --lon $(LON) \
		$(if $(ELEV),--elevation $(ELEV)) --out ../data/fixtures/planner/site_$(PLOT).json

check: check-repo check-backend check-frontend check-planner ## Everything CI runs

preflight: ## Check that MUSE_API_KEY can use the configured models (network; not in CI)
	$(UV) run python -m app.agent.llm.preflight

clean: ## Remove caches and build output
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache $(FRONTEND)/dist \
		$(PLANNER)/.pytest_cache $(PLANNER)/.mypy_cache $(PLANNER)/.ruff_cache
