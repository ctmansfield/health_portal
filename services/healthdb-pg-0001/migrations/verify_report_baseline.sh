#!/usr/bin/env bash
# verify_report_baseline.sh
# Automated verification script for report baseline migrations.
# Runs the up migration, the test assertions, a few smoke checks (SELECT and EXPLAIN), and then rolls back.
# Intended to be run in CI or locally. Does NOT leave created objects behind.

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")"/.. >/dev/null 2>&1 && pwd)
MIG_DIR="$ROOT_DIR/migrations"
UP_SQL="$MIG_DIR/001_report_baseline_up.sql"
TEST_SQL="$MIG_DIR/002_report_baseline_test.sql"
DOWN_SQL="$MIG_DIR/001_report_baseline_down.sql"

if [ -z "${HP_DSN:-}" ]; then
  echo "Error: HP_DSN is not set. Export HP_DSN to point to your test Postgres (e.g. postgresql://user:pass@host:port/dbname)"
  exit 2
fi

# Ensure psql available
if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql not found in PATH"
  exit 2
fi

# Ensure SQL files exist
for f in "$UP_SQL" "$TEST_SQL" "$DOWN_SQL"; do
  if [ ! -f "$f" ]; then
    echo "Missing required file: $f"
    exit 3
  fi
done

# On exit, always attempt to rollback (drop created objects). This is safe because down migration uses IF EXISTS.
cleanup() {
  echo "\n==> Running rollback (down migration) to clean up..."
  psql "$HP_DSN" -v ON_ERROR_STOP=1 -f "$DOWN_SQL" || true
}
trap cleanup EXIT

echo "==> Applying up migration: $UP_SQL"
psql "$HP_DSN" -v ON_ERROR_STOP=1 -f "$UP_SQL"

echo "==> Running schema assertions/test: $TEST_SQL"
psql "$HP_DSN" -v ON_ERROR_STOP=1 -f "$TEST_SQL"

echo "==> Running smoke SELECT against analytics.report_exec_summary"
psql "$HP_DSN" -c "SELECT id, title, result, signed_out_at FROM analytics.report_exec_summary LIMIT 5;"

echo "==> Running EXPLAIN ANALYZE for variant gene filter (shows index usage)"
psql "$HP_DSN" -c "EXPLAIN ANALYZE SELECT * FROM analytics.variant WHERE gene_symbol = 'TP53';"

# If we reach here, tests passed. Cleanup will run via trap.
echo "\nAll checks passed. Rollback will now be executed to leave the database unchanged."
exit 0
