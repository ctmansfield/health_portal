set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
. .venv/bin/activate || true
python jobs/export_findings.py --format ndjson | head -n 3 || true
python jobs/export_vitals_daily.py --format csv | head -n 3 || true
