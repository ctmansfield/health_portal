set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
bash "$ROOT/services/healthdb-pg-0001/scripts/refresh_views.sh"
"$ROOT/services/healthdb-pg-0001/scripts/psql.sh" -c "SELECT * FROM analytics.v_vitals_latest;"
"$ROOT/services/healthdb-pg-0001/scripts/psql.sh" -c "SELECT day, hr_median, spo2_min FROM analytics.mv_vitals_daily_wide ORDER BY day DESC LIMIT 7;"
"$ROOT/services/healthdb-pg-0001/scripts/psql.sh" -c "SELECT code_system, code, n FROM fhir_raw.v_observation_counts ORDER BY n DESC NULLS LAST LIMIT 10;"
"$ROOT/services/healthdb-pg-0001/scripts/psql.sh" -c "SELECT * FROM analytics.v_events_recent LIMIT 10;"
