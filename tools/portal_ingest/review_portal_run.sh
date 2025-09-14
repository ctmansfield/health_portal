
#!/usr/bin/env bash
# Review a staged run without committing to analytics.
# Usage: tools/portal_ingest/review_portal_run.sh <RUN_ID>
set -euo pipefail
RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: $0 <RUN_ID>" >&2
  exit 2
fi
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"

echo "[review] Staged rows (top 20) for run_id=${RUN_ID}:"
"${PSQL}" -c "SELECT person_id, provider, test_name, value_num, unit, effective_time, code_system, code FROM ingest_portal.stg_portal_labs WHERE run_id='${RUN_ID}' ORDER BY effective_time DESC NULLS LAST, person_id, test_name LIMIT 20;"

echo
echo "[review] Duplicates logged (top 20):"
"${PSQL}" -c "SELECT reason, details FROM ingest_portal.dup_log WHERE run_id='${RUN_ID}' LIMIT 20;"

echo
echo "[review] Rejections (top 20):"
"${PSQL}" -c "SELECT reason, provider, effective_time, parsed->>'test' AS test, parsed->>'value' AS value FROM ingest_portal.rejections WHERE run_id='${RUN_ID}' LIMIT 20;"

echo
echo "[review] Counts by code:"
"${PSQL}" -c "SELECT code_system, code, COUNT(*) AS n FROM ingest_portal.stg_portal_labs WHERE run_id='${RUN_ID}' GROUP BY 1,2 ORDER BY n DESC, code_system, code;"
