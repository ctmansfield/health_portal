.PHONY: help venv fmt lint test up down verify psql import-apple mirror-fhir dump

help:
	@echo "Targets: up, down, verify, psql, import-apple ZIP=..., mirror-fhir, dump"

venv:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip

up:
	cd services/healthdb-pg-0001 && ./scripts/up.sh

down:
	cd services/healthdb-pg-0001 && ./scripts/down.sh

verify:
	cd services/healthdb-pg-0001 && ./verify.sh

seed:
	@echo "Applying DB init migrations and seeding sample data"
	bash scripts/db/apply_migrations.sh
	. .venv/bin/activate && python jobs/seed_sample_data.py --genomics --findings --days 30

psql:
	cd services/healthdb-pg-0001 && ./scripts/psql.sh

import-apple:
	. .venv/bin/activate && python jobs/import_apple_health.py --zip "$(ZIP)" --person-id me --dsn "postgresql://health:health_pw@localhost:55432/health"

mirror-fhir:
	. .venv/bin/activate && python jobs/mirror_fhir_observations.py --dsn "postgresql://health:health_pw@localhost:55432/health"

dump:
	docker exec -t healthdb pg_dump -U health -d health > /mnt/nas_storage/backups/health_$(shell date +%F).sql

ai-scan:
	. .venv/bin/activate && python jobs/ai_daily_scan.py --dsn "$(HP_DSN)"

import-fhir:
	. .venv/bin/activate && python jobs/import_fhir_ndjson.py --file "$(FILE)" --dsn "$(HP_DSN)"

api:
	. .venv/bin/activate && HP_DSN="$(HP_DSN)" uvicorn app.api.main:app --host 0.0.0.0 --port 8800 --reload
.PHONY: anomalies-sql anomalies-list anomalies-set refresh-views

anomalies-sql:
\tservices/healthdb-pg-0001/scripts/psql.sh < services/healthdb-pg-0001/init/053_anomaly_thresholds.sql
\tservices/healthdb-pg-0001/scripts/psql.sh < services/healthdb-pg-0001/init/051_vitals_anomalies.sql

anomalies-list:
\tcurl -s "http://127.0.0.1:8810/api/anomalies/thresholds" | jq .

anomalies-set:
\tcurl -s -X PUT "http://127.0.0.1:8810/api/anomalies/thresholds/8867-4" \\
\t  -H 'Content-Type: application/json' \\
\t  -d '{"code":"8867-4","min_val":20,"max_val":210,"reason":"HR test","enabled":true}' | jq .

refresh-views:
\t. .venv/bin/activate && python jobs/refresh_views.py
