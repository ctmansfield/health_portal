#!/usr/bin/env bash
# Apply SQL files in services/healthdb-pg-0001/init in lexical order to the DB defined by HP_DSN
set -euo pipefail
DSN=${HP_DSN:-}
if [ -z "$DSN" ]; then
  echo "HP_DSN is not set. Export HP_DSN to point to your local test DB."
  exit 2
fi
MIG_DIR="services/healthdb-pg-0001/init"
if [ ! -d "$MIG_DIR" ]; then
  echo "Migration directory not found: $MIG_DIR"
  exit 1
fi
for f in $(ls "$MIG_DIR"/*.sql | sort); do
  echo "--- Applying $f"
  psql "$DSN" -v ON_ERROR_STOP=1 -f "$f"
done

echo "All init migrations applied."
