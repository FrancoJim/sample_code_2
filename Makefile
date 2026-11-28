# BEA Economic Data Pipeline — common tasks. Run `make` (or `make help`) to list them.

PYTHON  ?= python3
VENV    ?= .venv
BIN     := $(VENV)/bin
IMAGE   ?= bea-pipeline
TAG     ?= latest
BUCKET  ?= sample-sized-bucket-local
DATASET ?= gdp
YEAR    ?= 2023

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Local ─────────────────────────────────────────────────────────────────────

$(BIN)/activate: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"
	@touch $@

.PHONY: install
install: $(BIN)/activate ## Create .venv and install the app + dev tools

.PHONY: run
run: install ## Run the pipeline (needs BEA_API_KEY + AWS creds; BUCKET=, DATASET=, YEAR=)
	set -a; [ -f .env ] && . ./.env; set +a; \
	$(BIN)/bea-pipeline --bucket $(BUCKET) --dataset $(DATASET) --year $(YEAR)

.PHONY: lint
lint: install ## Lint and check formatting with ruff
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

.PHONY: fmt
fmt: install ## Auto-fix lint issues and format code
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

.PHONY: typecheck
typecheck: install ## Type-check with mypy
	$(BIN)/mypy sample_2

.PHONY: test
test: install ## Run tests with coverage (AWS and the BEA API are mocked)
	$(BIN)/pytest -v

.PHONY: check
check: lint typecheck test ## Lint + typecheck + tests (same as CI)

.PHONY: pre-commit-install
pre-commit-install: install ## Install the git pre-commit hooks
	$(BIN)/pre-commit install

.PHONY: lock
lock: ## Regenerate requirements.txt (pinned runtime deps for Docker)
	rm -rf .lockenv && $(PYTHON) -m venv .lockenv
	.lockenv/bin/pip install -q .
	{ echo "# Pinned runtime dependencies for the Docker image (tested versions)."; \
	  echo "# Regenerate with: make lock"; \
	  .lockenv/bin/pip freeze --exclude-editable | grep -vi '^sample.2'; } > requirements.txt
	rm -rf .lockenv build

# ── Docker ────────────────────────────────────────────────────────────────────

.PHONY: docker-build
docker-build: ## Build the production image
	docker build -f Dockerfile-prod -t $(IMAGE):$(TAG) .

.PHONY: docker-run
docker-run: docker-build ## Run the production image with .env (BUCKET=, DATASET=, YEAR=)
	docker run --rm --read-only --tmpfs /tmp --env-file .env -v "$(CURDIR)/data:/app/data" \
		$(IMAGE):$(TAG) --bucket $(BUCKET) --dataset $(DATASET) --year $(YEAR)

.PHONY: docker-test
docker-test: ## Run lint + typecheck + tests inside the dev image
	docker compose --profile dev build app-dev
	docker compose --profile dev run --rm --no-deps app-dev \
		sh -c "ruff check . && ruff format --check . && mypy sample_2 && pytest -v"

# ── Devcontainer (dev shell + LocalStack S3) ──────────────────────────────────

.PHONY: dc-build
dc-build: ## Build the devcontainer image
	docker compose -f .devcontainer/docker-compose.yml build

.PHONY: dc-up
dc-up: ## Start the devcontainer + LocalStack
	docker compose -f .devcontainer/docker-compose.yml up -d

.PHONY: dc-shell
dc-shell: ## Open a shell in the running devcontainer
	docker exec -it sample_code_2_devcontainer bash

.PHONY: dc-down
dc-down: ## Stop and remove the devcontainer + LocalStack
	docker compose -f .devcontainer/docker-compose.yml down

# ── Housekeeping ──────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove caches, build output, and .venv
	rm -rf $(VENV) build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
