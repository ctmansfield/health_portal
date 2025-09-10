set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
. .venv/bin/activate || true
python jobs/import_fhir_ndjson.py --file /mnt/nas_storage/incoming/sample.ndjson --dsn "${HP_DSN:-postgresql://health:health_pw@localhost:55432/health}" || true
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT count(*) AS fhir_count FROM fhir_raw.resources;"
