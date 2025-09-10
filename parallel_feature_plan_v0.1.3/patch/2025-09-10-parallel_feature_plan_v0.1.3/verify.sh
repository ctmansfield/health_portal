#!/usr/bin/env bash
set -euo pipefail
set -o pipefail
REQ_DOC="docs/reporting_scaffold/Parallel_Workstreams_and_Interface_Contracts.md"
REQ_CONTRACTS="core/contracts.yaml"
REQ_OPENAPI="api/openapi.genomics_reports.v1.yaml"

for f in "$REQ_DOC" "$REQ_CONTRACTS" "$REQ_OPENAPI"; do
  test -f "$f" || (echo "[fail] Missing $f" && exit 2)
  echo "[ok] Found $f"
done

# quick key presence check
grep -q "^db_schema_version:" "$REQ_CONTRACTS" || (echo "[fail] contracts.yaml missing db_schema_version" && exit 2)
grep -q "openapi: 3.1.0" "$REQ_OPENAPI" || (echo "[fail] openapi file not 3.1.0" && exit 2)

echo "[verify] All good."
