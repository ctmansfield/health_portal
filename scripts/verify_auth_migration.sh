#!/usr/bin/env bash
# Verify that auth migration tables exist in HP_DSN database.
set -euo pipefail
DSN=${HP_DSN:-}
if [ -z "$DSN" ]; then
  echo "HP_DSN not set. Export HP_DSN to run verification."
  exit 2
fi
psql "$DSN" -c "\dt analytics.*" > /dev/null
# Check expected tables
for t in users roles user_roles sessions auth_audit; do
  if ! psql "$DSN" -c "SELECT to_regclass('analytics.'||'$t')" -t | grep -q "\S"; then
    echo "Missing analytics.$t"
    exit 1
  fi
done

echo "Auth migration tables present."
