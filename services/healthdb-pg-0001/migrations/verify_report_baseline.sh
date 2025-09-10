#!/usr/bin/env bash
# verify_report_baseline.sh
# Automated verification script for report baseline migrations.
# Runs the up migration, the test assertions, a few smoke checks (SELECT and EXPLAIN), and then rolls back.
# Intended to be run in CI or locally. Does NOT leave created objects behind.
# Produces machine-readable JSON output to stdout for CI consumption, and verbose human logs to stderr.

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")"/.. >/dev/null 2>&1 && pwd)
MIG_DIR="$ROOT_DIR/migrations"
UP_SQL="$MIG_DIR/001_report_baseline_up.sql"
TEST_SQL="$MIG_DIR/002_report_baseline_test.sql"
DOWN_SQL="$MIG_DIR/001_report_baseline_down.sql"

# Output helpers
json_start() { echo -n '{'; }
json_kv() { printf '"%s": %s' "$1" "$2"; }
json_str() { printf '"%s"' "$(echo "$1" | sed 's/"/\\"/g')"; }

# We'll accumulate a JSON object in variables then print at the end
RESULT_STATUS="pass"
RESULT_MSG="All checks passed"
RESULT_DETAILS="{}"

if [ -z "${HP_DSN:-}" ]; then
  RESULT_STATUS="fail"
  RESULT_MSG="HP_DSN is not set"
  >&2 echo "Error: HP_DSN is not set. Export HP_DSN to point to your test Postgres (e.g. postgresql://user:pass@host:port/dbname)"
  json_start; json_kv status "$(json_str "$RESULT_STATUS")"; echo ,; json_kv message "$(json_str "$RESULT_MSG")"; echo '}';
  exit 2
fi

# Ensure psql available
if ! command -v psql >/dev/null 2>&1; then
  RESULT_STATUS="fail"
  RESULT_MSG="psql not found in PATH"
  >&2 echo "Error: psql not found in PATH"
  json_start; json_kv status "$(json_str "$RESULT_STATUS")"; echo ,; json_kv message "$(json_str "$RESULT_MSG")"; echo '}';
  exit 2
fi

# Ensure SQL files exist
for f in "$UP_SQL" "$TEST_SQL" "$DOWN_SQL"; do
  if [ ! -f "$f" ]; then
    RESULT_STATUS="fail"
    RESULT_MSG="Missing required file: $f"
    >&2 echo "$RESULT_MSG"
    json_start; json_kv status "$(json_str "$RESULT_STATUS")"; echo ,; json_kv message "$(json_str "$RESULT_MSG")"; echo '}';
    exit 3
  fi
done

# On exit, always attempt to rollback (drop created objects). This is safe because down migration uses IF EXISTS.
cleanup() {
  >&2 echo "\n==> Running rollback (down migration) to clean up..."
  psql "$HP_DSN" -v ON_ERROR_STOP=1 -f "$DOWN_SQL" || true
}
trap cleanup EXIT

# Run up migration and capture output
>&2 echo "==> Applying up migration: $UP_SQL"
if ! psql "$HP_DSN" -v ON_ERROR_STOP=1 -f "$UP_SQL" 2>&1 >/dev/null; then
  RESULT_STATUS="fail"
  RESULT_MSG="Up migration failed"
  >&2 echo "Up migration failed"
  json_start; json_kv status "$(json_str "$RESULT_STATUS")"; echo ,; json_kv message "$(json_str "$RESULT_MSG")"; echo '}';
  exit 4
fi

# Run test assertions
>&2 echo "==> Running schema assertions/test: $TEST_SQL"
if ! psql "$HP_DSN" -v ON_ERROR_STOP=1 -f "$TEST_SQL" 2>&1 >/dev/null; then
  RESULT_STATUS="fail"
  RESULT_MSG="Schema assertions failed"
  >&2 echo "Schema assertions failed"
  json_start; json_kv status "$(json_str "$RESULT_STATUS")"; echo ,; json_kv message "$(json_str "$RESULT_MSG")"; echo '}';
  exit 5
fi

# Run smoke SELECT and capture rows as JSON
>&2 echo "==> Running smoke SELECT against analytics.report_exec_summary"
SMOKE_JSON=$(psql "$HP_DSN" -At -F"," -c "SELECT id, coalesce(title,''), coalesce(result,''), coalesce(signed_out_at::text,'') FROM analytics.report_exec_summary LIMIT 5;" | awk 'BEGIN{print "["} NR>1{print ","} {printf("[\"%s\",\"%s\",\"%s\",\"%s\"]", $1,$2,$3,$4)} END{print "]"}')

# Run EXPLAIN ANALYZE and capture a few lines
>&2 echo "==> Running EXPLAIN ANALYZE for variant gene filter (shows index usage)"
EXPLAIN_OUT=$(psql "$HP_DSN" -c "EXPLAIN ANALYZE SELECT * FROM analytics.variant WHERE gene_symbol = 'TP53';" -t -A 2>&1 | sed -e 's/"/\\"/g' | python -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

# Build result JSON for CI
RESULT_STATUS="pass"
RESULT_MSG="All checks passed"
cat <<JSON
{
  "status": "${RESULT_STATUS}",
  "message": "${RESULT_MSG}",
  "smoke_sample": ${SMOKE_JSON:-[]},
  "explain": ${EXPLAIN_OUT:-""}
}
JSON

# If we reach here, tests passed. Cleanup will run via trap.
>&2 echo "\nAll checks passed. Rollback will now be executed to leave the database unchanged."
exit 0
