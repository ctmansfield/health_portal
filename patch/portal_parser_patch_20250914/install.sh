
#!/usr/bin/env bash
set -euo pipefail

# Detect repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"

echo "[install] Applying ingest schema SQL..."
services/healthdb-pg-0001/scripts/psql.sh < services/healthdb-pg-0001/init/056_portal_ingest_schema.sql

echo "[install] Creating Python venv and installing requirements..."
VENV_DIR="${REPO_ROOT}/.venv-portal-ingest"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
pip install -U pip
pip install -r tools/portal_ingest/requirements.txt

echo "[install] Done."
