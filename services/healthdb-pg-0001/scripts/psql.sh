#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# -T disables TTY so stdin redirection works; "$@" passes -c etc when used
docker compose exec -T -e PAGER=cat db \
  psql -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}" "$@"
