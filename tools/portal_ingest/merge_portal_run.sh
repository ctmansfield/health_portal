
#!/usr/bin/env bash
# Merge a staged run into analytics.data_events after review.
# Usage: tools/portal_ingest/merge_portal_run.sh <RUN_ID>
set -euo pipefail
RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: $0 <RUN_ID>" >&2
  exit 2
fi
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"

echo "[merge] Merging run ${RUN_ID} into analytics.data_events ..."
"${PSQL}" -v run_id="${RUN_ID}" < "${REPO_ROOT}/services/healthdb-pg-0001/init/057_portal_ingest_merge.sql"
echo "[merge] Done."
