#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/psql.sh -c "\di+ analytics.uq_events_person_metric_time"
./scripts/psql.sh -c "
  SELECT conname, conrelid::regclass AS on_table, conindid::regclass AS index_name
  FROM pg_constraint
  WHERE conname='uq_events_person_metric_time';
" || true
