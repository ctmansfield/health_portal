#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8080/fhir}"
echo "GET $BASE/metadata"
curl -fsS "$BASE/metadata" >/dev/null
echo "OK: metadata endpoint reachable."
