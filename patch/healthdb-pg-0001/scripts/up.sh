#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d
echo "Adminer: http://localhost:18080  (server: db, user: ${POSTGRES_USER:-health})"
