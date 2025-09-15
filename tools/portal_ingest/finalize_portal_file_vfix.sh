#!/usr/bin/env bash
set -euo pipefail
RUN_ID="${1:-}"; SRC="${2:-}"
[[ -z "${RUN_ID}" || -z "${SRC}" ]] && { echo "Usage: $0 RUN_ID FILEPATH" >&2; exit 2; }

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"
SQL="${REPO_ROOT}/tools/portal_ingest/sql/merge_one_run_portal_vfix.sql"
DEST_DIR="/mnt/nas_storage/imported"

[[ -x "${PSQL}" ]] || { echo "[finalize] ERROR: psql wrapper not found at ${PSQL}" >&2; exit 3; }
[[ -f "${SQL}"  ]] || { echo "[finalize] ERROR: merge SQL not found at ${SQL}" >&2; exit 4; }
[[ -f "${SRC}"  ]] || { echo "[finalize] ERROR: source file missing: ${SRC}" >&2; exit 5; }

echo "[merge] Merging run ${RUN_ID} into analytics.data_events ..."
"${PSQL}" -v RUN_ID="${RUN_ID}" -f "${SQL}"
echo "[merge] OK."

mkdir -p "${DEST_DIR}"
BN="$(basename -- "${SRC}")"
DEST="${DEST_DIR}/${BN}"
if [[ -e "${DEST}" ]]; then
  ts="$(date +%Y%m%d%H%M%S)"
  DEST="${DEST_DIR}/${BN}.${ts}"
fi
mv -n -- "${SRC}" "${DEST}"
echo "[finalize] Moved ${SRC} -> ${DEST}"
