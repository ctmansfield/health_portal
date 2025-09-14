#!/usr/bin/env bash
# Merge a staged run and then move the associated source file into /mnt/nas_storage/imported.
# Usage: tools/portal_ingest/finalize_portal_file.sh RUN_ID FILEPATH
set -euo pipefail
RUN_ID="${1:-}"
FILE="${2:-}"
DEST_DIR="/mnt/nas_storage/imported"

if [[ -z "${RUN_ID}" || -z "${FILE}" ]]; then
  echo "Usage: $0 RUN_ID FILEPATH" >&2
  exit 2
fi

if [[ ! -d "${DEST_DIR}" ]]; then
  echo "[error] Destination dir missing: ${DEST_DIR}" >&2
  exit 3
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"

# 1) merge into analytics
"${REPO_ROOT}/tools/portal_ingest/merge_portal_run.sh" "${RUN_ID}"

# 2) move file into imported (no overwrite; add timestamp if exists)
base="$(basename "${FILE}")"
target="${DEST_DIR}/${base}"

if [[ -e "${target}" ]]; then
  ts="$(date +%Y%m%d%H%M%S)"
  target="${DEST_DIR}/${base}.${ts}"
fi

mv -n -- "${FILE}" "${target}"
echo "[finalize] Moved ${FILE} -> ${target}"
