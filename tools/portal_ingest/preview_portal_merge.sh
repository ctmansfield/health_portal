#!/usr/bin/env bash
# Preview what WOULD be inserted into analytics.data_events for a given RUN_ID.
# Usage:
#   tools/portal_ingest/preview_portal_merge.sh RUN_ID [--csv /path/to/export.csv]

RUN_ID="${1:-}"; shift || true
if [ -z "$RUN_ID" ]; then
  echo "Usage: $0 RUN_ID [--csv /path/to/export.csv]" >&2
  exit 2
fi

CSV_OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --csv) CSV_OUT="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
PSQL="${REPO_ROOT}/services/healthdb-pg-0001/scripts/psql.sh"

# Core SELECT (anti-joined against analytics to avoid re-inserting existing rows)
SELECT_BODY="
  SELECT
    s.person_id,
    'lab'::text       AS kind,
    'portal'::text    AS source,
    s.code_system,
    s.code,
    s.test_name       AS code_display,
    s.value_num,
    s.unit,
    s.effective_time,
    jsonb_build_object(
      'run_id', s.run_id,
      'source_file', ir.source_file,
      'importer', 'portal_ingest_preview'
    ) AS meta,
    jsonb_build_object(
      'provider', s.provider,
      'flag', s.flag,
      'reference', s.reference_text,
      'src_line', s.src_line,
      'src_page', s.src_page,
      'src_order', s.src_order,
      'src_hash', s.src_hash
    ) AS raw
  FROM ingest_portal.stg_portal_labs s
  JOIN ingest_portal.import_run ir USING (run_id)
  WHERE s.run_id = '${RUN_ID}'::uuid
    AND NOT EXISTS (
      SELECT 1
      FROM analytics.data_events d
      WHERE d.person_id     = s.person_id
        AND d.code_system   = s.code_system
        AND d.code          = s.code
        AND d.effective_time= s.effective_time
        AND d.value_num     = s.value_num
        AND COALESCE(d.unit,'') = COALESCE(s.unit,'')
    )
"

# 0) Summary of what's staged
"$PSQL" -c "
SELECT
  COUNT(*) AS staged_rows,
  MIN(effective_time) AS min_effective_time,
  MAX(effective_time) AS max_effective_time
FROM ingest_portal.stg_portal_labs
WHERE run_id = '${RUN_ID}'::uuid;
"

# 1) Count that WOULD be inserted
"$PSQL" -c "
WITH new_rows AS (
  ${SELECT_BODY}
)
SELECT COUNT(*) AS would_insert FROM new_rows;
"

# 2) Per-code counts (top 50)
"$PSQL" -c "
WITH new_rows AS (${SELECT_BODY})
SELECT code, COUNT(*) AS n, MIN(effective_time) AS first_dt, MAX(effective_time) AS last_dt
FROM new_rows
GROUP BY 1
ORDER BY n DESC, code ASC
LIMIT 50;
"

# 3) Sample rows (most recent first)
"$PSQL" -c "
WITH new_rows AS (${SELECT_BODY})
SELECT person_id, kind, source, code_system, code, code_display, value_num, unit, effective_time
FROM new_rows
ORDER BY effective_time DESC, code ASC
LIMIT 50;
"

# 4) Optional CSV export (client-side)
if [ -n "${CSV_OUT}" ]; then
  echo "[preview] Exporting full would-be insert to: ${CSV_OUT}"
  mkdir -p "$(dirname "${CSV_OUT}")" 2>/dev/null || true
  "$PSQL" -A -F ',' -q -c "\copy ( ${SELECT_BODY} ) TO STDOUT WITH CSV HEADER" > "${CSV_OUT}"
  echo "[preview] Wrote ${CSV_OUT}"
fi
