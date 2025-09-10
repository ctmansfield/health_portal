set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
services/healthdb-pg-0001/scripts/psql.sh < services/healthdb-pg-0001/init/045_unique_keys.sql
. .venv/bin/activate || true
python jobs/map_fhir_to_events.py --dsn "${HP_DSN:-postgresql://health:health_pw@localhost:55432/health}" --person-id me --limit 200 || true
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT code_system, code, count(*) FROM analytics.data_events GROUP BY 1,2 ORDER BY 1,2;"
