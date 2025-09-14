#!/usr/bin/env bash
# Stage (only) each portal file and load into ingest_portal.* using the repo psql wrapper.
# No DSN or passwords on the CLI; relies on services/healthdb-pg-0001/scripts/psql.sh env.
# Usage: tools/portal_ingest/stage_portal_files.sh PERSON_ID [GLOB]
# Default GLOB: /mnt/nas_storage/import/portal_*
set -euo pipefail
PERSON_ID="${1:-}"
GLOB="${2:-/mnt/nas_storage/import/portal_*}"

if [[ -z "${PERSON_ID}" ]]; then
  echo "Usage: $0 PERSON_ID [GLOB]" >&2
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL_WRAPPER="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"
if [[ ! -x "${PSQL_WRAPPER}" ]]; then
  echo "[stage] ERROR: psql wrapper not found at ${PSQL_WRAPPER}" >&2
  exit 3
fi

source "${REPO_ROOT}/.venv-portal-ingest/bin/activate"

shopt -s nullglob
files=( ${GLOB} )
shopt -u nullglob

if (( ${#files[@]} == 0 )); then
  echo "[stage] No files matched: ${GLOB}" >&2
  exit 4
fi

echo "[stage] Found ${#files[@]} files to stage:"
printf '  %s
' "${files[@]}"

RUN_LIST="${REPO_ROOT}/portal_ingest_out/staged_runs_$(date +%Y%m%d%H%M%S).txt"
: > "${RUN_LIST}"

for f in "${files[@]}"; do
  [[ -f "${f}" ]] || { echo "[skip] Not a regular file: ${f}" >&2; continue; }

  echo
  echo "[stage] Parsing ${f} (dry-run to emit CSV logs)..."
  OUT="$(python tools/portal_ingest/ingest_portal.py --dry-run     --person-id "${PERSON_ID}"     --input "${f}"     --source-file "$(basename "${f}")" 2>&1 | tee /dev/fd/2 || true)"

  RUN_ID="$(echo "${OUT}" | sed -nE 's/.*\"run_id\": \"([0-9a-f-]{36})\".*/\1/p' | tail -n1)"
  if [[ -z "${RUN_ID}" ]]; then
    # fallback: find most recent dir under portal_ingest_out
    RUN_ID="$(ls -1dt "${REPO_ROOT}/portal_ingest_out"/*/ 2>/dev/null | head -n1 | xargs -I{} basename "{}" || true)"
  fi
  if [[ -z "${RUN_ID}" ]]; then
    echo "[error] Could not determine run_id for ${f}" >&2
    exit 5
  fi

  OUTDIR="${REPO_ROOT}/portal_ingest_out/${RUN_ID}"
  STAGED="${OUTDIR}/staged.csv"
  REJ="${OUTDIR}/rejections.csv"
  DUP="${OUTDIR}/duplicates.csv"

  echo "[stage] Loading staged rows via psql wrapper..."
  "${PSQL_WRAPPER}" -c "INSERT INTO ingest_portal.import_run (run_id, source_file, person_id, importer_version) VALUES ('${RUN_ID}', '$(basename "${f}")', '${PERSON_ID}', 'portal_ingest_v1') ON CONFLICT (run_id) DO NOTHING;"
  if [[ -s "${STAGED}" ]]; then
    "${PSQL_WRAPPER}" -c "\\copy ingest_portal.stg_portal_labs(run_id,person_id,provider,test_name,value_num,unit,flag,reference_text,effective_time,code_system,code,src_line,src_page,src_order,src_hash) FROM '${STAGED}' CSV HEADER;"
  else
    echo "[stage] NOTE: staged.csv is empty for ${f}"
  fi

  if [[ -s "${REJ}" ]]; then
    "${PSQL_WRAPPER}" -c "\\copy ingest_portal.rejections(run_id,reason,provider,raw_text,effective_time,parsed) FROM '${REJ}' CSV HEADER;"
  fi
  if [[ -s "${DUP}" ]]; then
    "${PSQL_WRAPPER}" -c "\\copy ingest_portal.dup_log(run_id,src_hash,reason,details) FROM '${DUP}' CSV HEADER;"
  fi

  echo "${RUN_ID}  ${f}" | tee -a "${RUN_LIST}"
done

echo
echo "[stage] Wrote run list: ${RUN_LIST}"
echo "[stage] Review with:   tools/portal_ingest/review_portal_run.sh <RUN_ID>"
echo "[stage] Finalize with: tools/portal_ingest/finalize_portal_file.sh <RUN_ID> <FILE>"
