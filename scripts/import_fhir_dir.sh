#!/usr/bin/env bash
set -euo pipefail
DIR="${1:-}"
DSN="${2:-${HP_DSN:-}}"
[[ -d "$DIR" ]] || { echo "usage: $0 /path/to/ndjson_dir [DSN]"; exit 1; }
[[ -n "$DSN" ]] || { echo "Set HP_DSN or pass DSN as 2nd arg"; exit 1; }

shopt -s nullglob
for f in "$DIR"/*.ndjson "$DIR"/*.ndjson.gz; do
  echo "[import] $f"
  python jobs/validate_ndjson.py --file "$f" || true
  python jobs/import_fhir_ndjson.py --file "$f" --dsn "$DSN"
done
echo "Done."
