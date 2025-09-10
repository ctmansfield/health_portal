#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   FAST=1 scripts/verify_import_fast.sh     # default: fast mode
#   FAST=0 scripts/verify_import_fast.sh     # full mode (can be slower)
#   TIMEOUT=5s scripts/verify_import_fast.sh # per-query timeout (default 5s)
#   VIEWS_TIMEOUT=20s scripts/verify_import_fast.sh # timeout for final views section

FAST="${FAST:-1}"
TIMEOUT="${TIMEOUT:-5s}"
VIEWS_TIMEOUT="${VIEWS_TIMEOUT:-20s}"   # slightly higher: views often wait on MV refresh / IO

_psql() {
  local q="$1"
  services/healthdb-pg-0001/scripts/psql.sh -v ON_ERROR_STOP=1 -A -F '|' -t -c "SET LOCAL statement_timeout='${TIMEOUT}'; ${q}"
}

_psql_views() {
  local q="$1"
  services/healthdb-pg-0001/scripts/psql.sh -v ON_ERROR_STOP=1 -A -F '|' -t -c "SET LOCAL statement_timeout='${VIEWS_TIMEOUT}'; ${q}"
}

echo "== FHIR resource counts =="
_psql "SELECT resource_type, COUNT(*) AS n
       FROM fhir_raw.resources GROUP BY 1 ORDER BY 1;"

echo
echo "== Totals (should be close to ~250 per your manifest) =="
_psql "SELECT COUNT(*) AS total FROM fhir_raw.resources;"

echo
echo "== Observation date range =="
_psql "WITH flat AS (
         SELECT (resource->>'effectiveDateTime')::timestamptz AS t
         FROM fhir_raw.resources WHERE resource_type='Observation'
       )
       SELECT MIN(t), MAX(t), COUNT(*) FROM flat;"

echo
echo "== Sample Observations (latest 5) =="
_psql "SELECT (resource->>'id') AS id,
              (resource->>'effectiveDateTime')::timestamptz AS effective_time,
              resource#>>'{code,coding,0,code}' AS code,
              (resource#>>'{valueQuantity,value}')::float AS value_num
       FROM fhir_raw.resources
       WHERE resource_type='Observation'
       ORDER BY imported_at DESC
       LIMIT 5;"

echo
echo "== analytics.data_events summary =="
_psql "SELECT MIN(effective_time), MAX(effective_time), COUNT(*) FROM analytics.data_events;"

if [[ "$FAST" == "0" ]]; then
  echo
  echo "== (full) counts by code_system, code =="
  _psql "SELECT code_system, code, COUNT(*) AS n
         FROM analytics.data_events
         GROUP BY 1,2 ORDER BY 1,2;"
else
  echo
  echo "== (fast) top 10 codes by recent activity =="
  _psql "SELECT code_system, code, COUNT(*) AS n
         FROM analytics.data_events
         WHERE effective_time >= now() - interval '14 days'
         GROUP BY 1,2 ORDER BY n DESC LIMIT 10;"
fi

echo
echo "== duplicates under unique key (should be zero) =="
HAS_UQ=$(_psql "SELECT 1
                FROM pg_indexes
                WHERE schemaname='analytics'
                  AND indexname='uq_events_person_metric_time'
                LIMIT 1;" || true)
if [[ -n "$HAS_UQ" ]]; then
  echo "uq_events_person_metric_time present: OK (skipping heavy duplicate scan)"
else
  if [[ "$FAST" == "0" ]]; then
    _psql "SELECT person_id, code_system, code, effective_time, COUNT(*) AS c
           FROM analytics.data_events
           WHERE value_num IS NOT NULL
             AND code_system IS NOT NULL
             AND code IS NOT NULL
             AND effective_time IS NOT NULL
           GROUP BY 1,2,3,4 HAVING COUNT(*)>1
           ORDER BY c DESC LIMIT 10;"
  else
    echo "FAST mode: skipped (set FAST=0 for full duplicate probe)"
  fi
fi

echo
echo "== vitals views (snippets) =="
# Use a slightly longer timeout and an index-friendly WHERE on the MV
_psql_views "SELECT * FROM analytics.v_vitals_latest LIMIT 5;"
_psql_views "SELECT day, hr_median, spo2_min
             FROM analytics.mv_vitals_daily_wide
             WHERE day >= (current_date - 120)       -- small range to ensure index use
             ORDER BY day DESC
             LIMIT 7;"
