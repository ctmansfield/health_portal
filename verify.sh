#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8800"

echo "==> Checking /findings (latest 5)"
curl -s "${BASE}/findings?limit=5" | jq .

echo
echo "==> Checking /vitals/daily (latest 5)"
curl -s "${BASE}/vitals/daily?limit=5" | jq .

echo
echo "==> Triggering /fhir/import (dry run, limit 2)"
curl -s -X POST "${BASE}/fhir/import?person_id=me&limit=2" | jq .
