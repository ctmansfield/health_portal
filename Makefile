.PHONY: help venv fmt lint test up down verify psql import-apple mirror-fhir dump docs

help:
	@echo "Targets: up, down, verify, psql, import-apple ZIP=..., mirror-fhir, dump, docs"

venv:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip

up:
	cd services/healthdb-pg-0001 && ./scripts/up.sh

down:
	cd services/healthdb-pg-0001 && ./scripts/down.sh

verify:
	cd services/healthdb-pg-0001 && ./verify.sh

psql:
	cd services/healthdb-pg-0001 && ./scripts/psql.sh

import-apple:
	. .venv/bin/activate && python jobs/import_apple_health.py --zip "$(ZIP)" --person-id me --dsn "postgresql://health:health_pw@localhost:55432/health"

mirror-fhir:
	. .venv/bin/activate && python jobs/mirror_fhir_observations.py --dsn "postgresql://health:health_pw@localhost:55432/health"

dump:
	docker exec -t healthdb pg_dump -U health -d health > /mnt/nas_storage/backups/health_$(shell date +%F).sql

docs:
	python scripts/docs/reindex_docs.py
	python scripts/docs/build_catalog.py
	python scripts/docs/build_adr_index.py
	python scripts/docs/build_contracts_registry.py
	python scripts/docs/build_code_map.py
	python scripts/docs/build_glossary_synonyms.py
	python scripts/docs/staleness_report.py
	python scripts/docs/link_check.py

ai-scan:
	. .venv/bin/activate && python jobs/ai_daily_scan.py --dsn "$(HP_DSN)"

import-fhir:
	. .venv/bin/activate && python jobs/import_fhir_ndjson.py --file "$(FILE)" --dsn "$(HP_DSN)"

api:
	. .venv/bin/activate && HP_DSN="$(HP_DSN)" uvicorn app.api.main:app --host 0.0.0.0 --port 8800 --reload


# >>> HAPI FHIR TARGETS >>>
HAPI_COMPOSE := ops/hapi_fhir/docker-compose.yml
HAPI_ENV := ops/hapi_fhir/.env

.PHONY: up-hapi down-hapi logs-hapi reset-hapi seed-hapi smoke-hapi

up-hapi:
	@if [ -f $(HAPI_ENV) ]; then export $$(grep -v '^#' $(HAPI_ENV) | xargs); fi; \
	docker compose -f $(HAPI_COMPOSE) up -d

down-hapi:
	docker compose -f $(HAPI_COMPOSE) down

logs-hapi:
	docker compose -f $(HAPI_COMPOSE) logs -f

reset-hapi: down-hapi
	rm -rf data/postgres

smoke-hapi:
	bash ops/hapi_fhir/smoke.sh

seed-hapi:
	bash ops/hapi_fhir/seed.sh
# <<< HAPI FHIR TARGETS <<<


# >>> APPLE HEALTH TARGETS >>>
.PHONY: apple-import apple-post apple-validate

APPLE_EXPORT ?= ~/Downloads/apple_health/export.xml
APPLE_OUT ?= /tmp/apple_to_fhir.json
FHIR_BASE ?= http://localhost:8080/fhir

apple-import:
	@bash ops/apple_health/convert.sh $(APPLE_EXPORT) $(APPLE_OUT) --subject=Patient/example

apple-post:
	@curl -sS -X POST "$(FHIR_BASE)" -H "Content-Type: application/fhir+json" --data-binary @$(APPLE_OUT) | jq .

apple-validate:
	@curl -sS -X POST "$(FHIR_BASE)/$validate" -H "Content-Type: application/fhir+json" --data-binary @$(APPLE_OUT) | jq .issue[]
# <<< APPLE HEALTH TARGETS <<<<
