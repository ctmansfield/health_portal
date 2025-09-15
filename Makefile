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
