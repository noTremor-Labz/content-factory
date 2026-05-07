BOOTSTRAP_PYTHON ?= python3
PYTHON_BIN ?= .venv/bin/python
PYTHONPATH_VALUE := apps/api/src:apps/worker/src
PYTHON_SOURCES := apps/api/src apps/api/tests apps/worker/src apps/worker/tests scripts
PYTHON_TYPECHECK_SOURCES := apps/api/src apps/worker/src scripts
OPENAPI_OUTPUT := packages/contracts/openapi/content-factory.openapi.json

.PHONY: install install-node install-python lint-web typecheck-web test-web test-web-e2e lint-api typecheck-api test-api migrate-api dev-web dev-api dev-watchdog export-openapi generate-contracts

install: install-node install-python

install-node:
	pnpm install

install-python:
	$(BOOTSTRAP_PYTHON) -m venv .venv
	$(PYTHON_BIN) -m pip install --upgrade pip
	$(PYTHON_BIN) -m pip install -e '.[dev]'

lint-web:
	pnpm --dir apps/web lint

typecheck-web:
	pnpm --dir apps/web typecheck

test-web:
	pnpm --dir apps/web test --run

test-web-e2e:
	pnpm --dir apps/web test:e2e

lint-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m ruff check $(PYTHON_SOURCES)

typecheck-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m mypy $(PYTHON_TYPECHECK_SOURCES)

test-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m pytest

migrate-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m alembic upgrade head

dev-web:
	pnpm --dir apps/web dev

dev-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m uvicorn content_factory_api.app:create_app --factory --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload

dev-watchdog:
	$(PYTHON_BIN) scripts/dev_watchdog.py

export-openapi:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m content_factory_api.export_openapi --output $(OPENAPI_OUTPUT)

generate-contracts: export-openapi
	pnpm --dir packages/contracts generate
