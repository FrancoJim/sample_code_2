.PHONY: install lint lint-fix test \
        run-dev run-prod docker-build docker-test \
        dc-up dc-down dc-build dc-shell \
        pre-commit-install clean

# ── Local development ─────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt

lint:
	ruff check .
	black --check .
	isort --check .

lint-fix:
	ruff check --fix .
	black .
	isort .

test:
	pytest --tb=short -v

pre-commit-install:
	pre-commit install

# ── App Docker (prod/dev/test images) ─────────────────────────────────────────

run-dev:
	docker compose --profile dev up --build

run-prod:
	docker compose --profile prod up --build

docker-test:
	docker compose --profile test up --build

docker-build:
	docker build -f Dockerfile-prod -t sample_2:latest .

# ── Devcontainer ──────────────────────────────────────────────────────────────

dc-build:
	docker compose -f .devcontainer/docker-compose.yml build

dc-up:
	docker compose -f .devcontainer/docker-compose.yml up -d

dc-down:
	docker compose -f .devcontainer/docker-compose.yml down

dc-shell:
	docker exec -it sample_code_2_devcontainer bash

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache dist build
