#!/usr/bin/env bash
# Wrapper-only staging that doesn't rely on container file mounts.
set -euo pipefail
PERSON_ID="${1:-}"; GLOB="${2:-/mnt/nas_storage/import/portal_*}"
[[ -z "${PERSON_ID}" ]] && { echo "Usage: $0 PERSON_ID [GLOB]" >&2; exit 2; }

PORTAL_OUTDIR_BASE="${PORTAL_OUTDIR_BASE:-/mnt/nas_storage/ingest/portal_ingest_out}"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"
[[ -x "${PSQL}" ]] || { echo "[stage] ERROR: psql wrapper not found at ${PSQL}" >&2; exit 3; }

source "${REPO_ROOT}/.venv-portal-ingest/bin/activate"

shopt -s nullglob; files=( ${GLOB} ); shopt -u nullglob
(( ${#files[@]} )) || { echo "[stage] No files matched: ${GLOB}" >&2; exit 4; }
echo "[stage] Found ${#files[@]} files to stage:"; printf '  %s\n' "${files[@]}"

mkdir -p "${REPO_ROOT}/portal_ingest_out"
RUN_LIST="${REPO_ROOT}/portal_ingest_out/staged_runs_$(date +%Y%m%d%H%M%S).txt"; : > "${RUN_LIST}"

copy_csv_stdin () {
  local csv="$1" table="$2" cols="$3"
  [[ -s "${csv}" ]] || { echo "[stage] NOTE: ${csv##*/} missing or empty; skipping ${table}"; return 0; }
  echo "[stage] COPY -> ${table} (${csv})"
  { cat "${csv}"; echo '\.'; } | "${PSQL}" -v ON_ERROR_STOP=1 -c "COPY ${table} (${cols}) FROM STDIN WITH (FORMAT csv, HEADER true)"
}

for f in "${files[@]}"; do
  [[ -f "${f}" ]] || { echo "[skip] Not a file: ${f}" >&2; continue; }
  echo; echo "[stage] Parsing ${f} (dry-run to ${PORTAL_OUTDIR_BASE})..."
  OUT="$(PORTAL_OUTDIR_BASE="${PORTAL_OUTDIR_BASE}" \
        python tools/portal_ingest/ingest_portal_vfix2.py \
          --dry-run --person-id "${PERSON_ID}" --input "${f}" --source-file "$(basename "${f}")" 2>&1 | tee /dev/fd/2)"

  RUN_ID="$(echo "${OUT}" | sed -nE 's/.*"run_id": "([0-9a-f-]{36})".*/\1/p' | tail -n1)"
  [[ -n "${RUN_ID}" ]] || { echo "[stage] ERROR: could not find run_id in output for ${f}" >&2; exit 5; }

  OUTDIR="${PORTAL_OUTDIR_BASE}/${RUN_ID}"
  [[ -d "${OUTDIR}" ]] || { echo "[stage] ERROR: expected OUTDIR missing: ${OUTDIR}" >&2; exit 6; }

  STAGED="${OUTDIR}/staged.csv"; REJ="${OUTDIR}/rejections.csv"; DUP="${OUTDIR}/duplicates.csv"
  ls -l "${OUTDIR}" || true

  echo "[stage] Upserting import_run..."
  "${PSQL}" -c "INSERT INTO ingest_portal.import_run (run_id, source_file, person_id, importer_version)
                VALUES ('${RUN_ID}', '$(basename "${f}")', '${PERSON_ID}', 'portal_ingest_vfix2')
                ON CONFLICT (run_id) DO NOTHING;"

  copy_csv_stdin "${STAGED}" "ingest_portal.stg_portal_labs" "run_id,person_id,provider,test_name,value_num,unit,flag,reference_text,effective_time,code_system,code,src_line,src_page,src_order,src_hash"
  copy_csv_stdin "${REJ}"    "ingest_portal.rejections"      "run_id,reason,provider,raw_text,effective_time,parsed"
  copy_csv_stdin "${DUP}"    "ingest_portal.dup_log"         "run_id,src_hash,reason,details"

  echo "${RUN_ID}  ${f}" | tee -a "${RUN_LIST}"
done

echo; echo "[stage] Wrote run list: ${RUN_LIST}"
echo "[stage] Review:   tools/portal_ingest/review_portal_run.sh <RUN_ID>"
echo "[stage] Finalize: tools/portal_ingest/finalize_portal_file.sh <RUN_ID> <FILE>"
