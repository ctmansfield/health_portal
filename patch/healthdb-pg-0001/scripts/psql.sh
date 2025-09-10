#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -e PAGER=cat db psql -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}"
