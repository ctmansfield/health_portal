#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="$ROOT/.venv_warehouse"
python3 -m venv "$VENV"
. "$VENV/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r "$ROOT/ops/warehouse/requirements.txt"
echo "VENV ready at $VENV"
