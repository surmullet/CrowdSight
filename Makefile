.PHONY: help check test dev web openapi lint clean

PYTHON ?= .venv/Scripts/python.exe
PYTEST ?= .venv/Scripts/pytest.exe
RUFF ?= .venv/Scripts/ruff.exe
MYPY ?= .venv/Scripts/mypy.exe

help:
	@echo "CrowdSight Engineering Makefile"
	@echo "  make check    - Run all linters, type checks, tests, and semantic invariants"
	@echo "  make test     - Run backend pytest test suite with coverage report"
	@echo "  make lint     - Run ruff linter and semantic invariant checker"
	@echo "  make dev      - Start FastAPI backend development server"
	@echo "  make web      - Start Vite frontend development server"
	@echo "  make openapi  - Export OpenAPI specification to contracts/app-v1/openapi.json"
	@echo "  make clean    - Remove cache and temporary test artifacts"

check:
	$(RUFF) check src/crowdsight/service tests
	$(MYPY) src/crowdsight/service
	$(PYTHON) scripts/semantic_lint.py
	$(PYTEST)
	cd web && pnpm run check

test:
	$(PYTEST) --cov=src/crowdsight/service --cov-report=term-missing --cov-report=html

lint:
	$(RUFF) check src/crowdsight/service tests
	$(PYTHON) scripts/semantic_lint.py

dev:
	$(PYTHON) -m uvicorn crowdsight.service.api.app:app --reload --host 127.0.0.1 --port 8001

web:
	cd web && pnpm run dev

openapi:
	$(PYTHON) -c "import json; from crowdsight.service.api.app import app; open('contracts/app-v1/openapi.json', 'w').write(json.dumps(app.openapi(), indent=2))"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
