#!/usr/bin/env bash
set -euo pipefail

# Apply genomics-related migrations to the HP_DSN database.
# Usage: HP_DSN=... bash scripts/db/apply_genomics_migrations.sh

DSN=${HP_DSN:-}
if [ -z "$DSN" ]; then
  echo "HP_DSN not set. Set HP_DSN or edit this script to supply connection args." >&2
  exit 1
fi

SQL1=services/healthdb-pg-0001/init/043_reports_views.sql
SQL2=services/healthdb-pg-0001/init/044_genomics_reports.sql

echo "Applying $SQL1 to $DSN"
psql "$DSN" -f "$SQL1"

echo "Applying $SQL2 to $DSN"
psql "$DSN" -f "$SQL2"

echo "Migrations applied."
