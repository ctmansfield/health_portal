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
# Try to autodetect if not set; falls back to /fhir
FHIR_BASE ?= $(shell bash /incoming/discover_fhir_base.sh 2>/dev/null || echo http://localhost:8080/fhir)

apple-import:
	@bash ops/apple_health/convert.sh $(APPLE_EXPORT) $(APPLE_OUT) --subject=Patient/example

# Posts a transaction Bundle to the FHIR base.
# - Forces JSON via Accept + _format=json
# - Follows redirects and preserves POST
# - Saves headers/body when not JSON for inspection
apple-post:
	@BASE="$(FHIR_BASE)"; URL="$${BASE%/}?_format=json"; \
	echo "POST $(APPLE_OUT) -> $$URL"; \
	curl -sS -L --post301 --post302 --post303 \
	  -X POST "$$URL" \
	  -H "Content-Type: application/fhir+json" \
	  -H "Accept: application/fhir+json" \
	  --data-binary @$(APPLE_OUT) \
	  -D /tmp/hapi_apple_post.headers \
	  -o /tmp/hapi_apple_post.out; \
	CT=$$(awk 'BEGIN{IGNORECASE=1}/^content-type:/{print $$2}' /tmp/hapi_apple_post.headers | tr -d '\r'); \
	if echo "$$CT" | grep -qi json; then jq . </tmp/hapi_apple_post.out; \
	else echo "Non-JSON (Content-Type=$$CT). First 200 bytes:"; head -c 200 /tmp/hapi_apple_post.out; echo; exit 1; fi

apple-validate:
	@BASE="$(FHIR_BASE)"; URL="$${BASE%/}/$validate?_format=json"; \
	curl -sS -L \
	  -H "Content-Type: application/fhir+json" \
	  -H "Accept: application/fhir+json" \
	  -X POST "$$URL" \
	  --data-binary @$(APPLE_OUT) | jq .issue[]
# <<< APPLE HEALTH TARGETS >>>


# >>> VA BLUE BUTTON TARGETS >>>
.PHONY: va-import va-post

VA_BB_TXT ?= ~/Downloads/VA-Blue-Button.txt
VA_BB_OUT ?= /tmp/va_bb_to_fhir.json
# Try autodiscovery if present; else default to local stack on 8085
FHIR_BASE ?= $(shell bash /incoming/discover_fhir_base.sh 2>/dev/null || echo http://localhost:8085/fhir)

va-import:
	@bash ops/va_bb/convert.sh $(VA_BB_TXT) $(VA_BB_OUT) --subject=Patient/example

va-post:
	@BASE="$(FHIR_BASE)"; URL="$${BASE%/}?_format=json"; \
	echo "POST $(VA_BB_OUT) -> $$URL"; \
	curl -sS -L --post301 --post302 --post303 \
	  -X POST "$$URL" \
	  -H "Content-Type: application/fhir+json" \
	  -H "Accept: application/fhir+json" \
	  --data-binary @$(VA_BB_OUT) \
	  -D /tmp/hapi_va_post.headers \
	  -o /tmp/hapi_va_post.out; \
	CT=$$(awk 'BEGIN{IGNORECASE=1}/^content-type:/{print $$2}' /tmp/hapi_va_post.headers | tr -d '\r'); \
	if echo "$$CT" | grep -qi json; then jq . </tmp/hapi_va_post.out; \
	else echo "Non-JSON (Content-Type=$$CT). First 200 bytes:"; head -c 200 /tmp/hapi_va_post.out; echo; exit 1; fi
# <<< VA BLUE BUTTON TARGETS >>>

# >>> FHIR EXPORT TARGETS >>>
.PHONY: fhir-export

FHIR_BASE ?= $(shell bash /incoming/discover_fhir_base.sh 2>/dev/null || echo http://localhost:8085/fhir)
FHIR_SUBJECT ?= Patient/example
LABS_CSV ?= /tmp/labs.csv
MEDS_CSV ?= /tmp/meds.csv

fhir-export:
	@python3 ops/fhir/export_fhir.py \
		--base $(FHIR_BASE) \
		--subject $(FHIR_SUBJECT) \
		--labs-out $(LABS_CSV) \
		--meds-out $(MEDS_CSV)
# <<< FHIR EXPORT TARGETS >>>
