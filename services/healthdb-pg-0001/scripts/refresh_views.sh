#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/psql.sh < init/041_events_views.sql
./scripts/psql.sh < init/042_fhir_flat_views.sql
for mv in analytics.mv_events_daily analytics.mv_vitals_daily_wide analytics.mv_daily_vitals; do
  ./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW CONCURRENTLY $mv;" \
  || ./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW $mv;"
done
echo "Views applied & MVs refreshed."
