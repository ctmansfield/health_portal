#!/usr/bin/env bash
set -euo pipefail
echo "[verify] contracts.yaml presence"
test -f core/contracts.yaml && echo "[ok] contracts.yaml found" || (echo "[fail] core/contracts.yaml missing" && exit 2)

echo "[verify] OpenAPI presence"
test -f api/openapi.genomics_reports.v1.yaml && echo "[ok] openapi found" || (echo "[fail] openapi missing" && exit 2)

if command -v python >/dev/null 2>&1; then
  python - <<'PY'
import re, sys
# Minimal check: API version alignment (best-effort without YAML lib)
openapi = open('api/openapi.genomics_reports.v1.yaml','r',encoding='utf-8').read()
m = re.search(r'\n\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+|[0-9]+\.[0-9]+)', openapi)
print("[ok] OpenAPI version:", m.group(1) if m else "unknown")
PY
fi

# Optional validators if installed
if python -c "import jsonschema" 2>/dev/null; then
  echo "[info] jsonschema available (add your schema tests here)"
fi
if python -c "import openapi_spec_validator" 2>/dev/null; then
  echo "[info] openapi-spec-validator available (basic validation)"
  python - <<'PY'
from openapi_spec_validator import validate_spec
import yaml, sys
with open('api/openapi.genomics_reports.v1.yaml','r',encoding='utf-8') as f:
    spec = yaml.safe_load(f)
validate_spec(spec)
print("[ok] OpenAPI spec validated")
PY
fi

echo "[verify] done"

# Run DB migration verification script for report baseline if HP_DSN is provided
if [ -n "${HP_DSN:-}" ]; then
  echo "[verify] Running DB migration verification for report baseline"
  services/healthdb-pg-0001/migrations/verify_report_baseline.sh
fi
