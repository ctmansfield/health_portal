#!/usr/bin/env bash
# Wrapper-only staging: dry-run to CSVs, then \copy via repo psql wrapper. No DSN on CLI.
set -euo pipefail
PERSON_ID="${1:-}"; GLOB="${2:-/mnt/nas_storage/import/portal_*}"
[[ -z "${PERSON_ID}" ]] && { echo "Usage: $0 PERSON_ID [GLOB]" >&2; exit 2; }

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"
[[ -x "${PSQL}" ]] || { echo "[stage] ERROR: psql wrapper not found at ${PSQL}" >&2; exit 3; }

source "${REPO_ROOT}/.venv-portal-ingest/bin/activate"

shopt -s nullglob; files=( ${GLOB} ); shopt -u nullglob
(( ${#files[@]} )) || { echo "[stage] No files matched: ${GLOB}" >&2; exit 4; }
echo "[stage] Found ${#files[@]} files to stage:"; printf '  %s\n' "${files[@]}"

mkdir -p "${REPO_ROOT}/portal_ingest_out"
RUN_LIST="${REPO_ROOT}/portal_ingest_out/staged_runs_$(date +%Y%m%d%H%M%S).txt"; : > "${RUN_LIST}"

for f in "${files[@]}"; do
  [[ -f "${f}" ]] || { echo "[skip] Not a file: ${f}" >&2; continue; }
  echo; echo "[stage] Parsing ${f} (dry-run)..."
  OUT="$(python tools/portal_ingest/ingest_portal_vfix.py --dry-run --person-id "${PERSON_ID}" --input "${f}" --source-file "$(basename "${f}")" 2>&1 | tee /dev/fd/2)"
  RUN_ID="$(echo "${OUT}" | sed -nE 's/.*"run_id": "([0-9a-f-]{36})".*/\1/p' | tail -n1)"
  [[ -n "${RUN_ID}" ]] || { echo "[stage] ERROR: could not find run_id in output for ${f}" >&2; exit 5; }
  OUTDIR="${REPO_ROOT}/portal_ingest_out/${RUN_ID}"; [[ -d "${OUTDIR}" ]] || { echo "[stage] ERROR: missing ${OUTDIR}" >&2; exit 6; }

  STAGED="${OUTDIR}/staged.csv"; REJ="${OUTDIR}/rejections.csv"; DUP="${OUTDIR}/duplicates.csv"
  echo "[stage] Loading via psql wrapper..."
  "${PSQL}" -c "INSERT INTO ingest_portal.import_run (run_id, source_file, person_id, importer_version) VALUES ('${RUN_ID}', '$(basename "${f}")', '${PERSON_ID}', 'portal_ingest_vfix') ON CONFLICT (run_id) DO NOTHING;"
  if [[ -s "${STAGED}" ]]; then
    "${PSQL}" -c "\copy ingest_portal.stg_portal_labs(run_id,person_id,provider,test_name,value_num,unit,flag,reference_text,effective_time,code_system,code,src_line,src_page,src_order,src_hash) FROM '${STAGED}' CSV HEADER;"
  else
    echo "[stage] NOTE: staged.csv empty"
  fi
  if [[ -s "${REJ}" ]]; then
    "${PSQL}" -c "\copy ingest_portal.rejections(run_id,reason,provider,raw_text,effective_time,parsed) FROM '${REJ}' CSV HEADER;"
  fi
  if [[ -s "${DUP}" ]]; then
    "${PSQL}" -c "\copy ingest_portal.dup_log(run_id,src_hash,reason,details) FROM '${DUP}' CSV HEADER;"
  fi

  echo "${RUN_ID}  ${f}" | tee -a "${RUN_LIST}"
done

echo; echo "[stage] Wrote run list: ${RUN_LIST}"
echo "[stage] Review:   tools/portal_ingest/review_portal_run.sh <RUN_ID>"
echo "[stage] Finalize: tools/portal_ingest/finalize_portal_file.sh <RUN_ID> <FILE>"
