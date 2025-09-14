
#!/usr/bin/env bash
set -euo pipefail

# Usage: ./verify.sh PERSON_ID [DAYS]
PERSON_ID="${1:-person_001}"
DAYS="${2:-30}"

echo "[verify] Recent liver codes present in analytics.data_events:"
services/healthdb-pg-0001/scripts/psql.sh -A -F '|' -t -c "
  SELECT code, COUNT(*) AS n, MIN(effective_time), MAX(effective_time)
  FROM analytics.data_events
  WHERE code_system='LOINC' AND code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
  GROUP BY 1 ORDER BY n DESC;
"

echo "[verify] Sample rows for ${PERSON_ID} (last ${DAYS} days):"
services/healthdb-pg-0001/scripts/psql.sh -A -F '|' -t -c "
  SELECT person_id, code_system, code, value_num, unit, effective_time
  FROM analytics.data_events
  WHERE person_id='${PERSON_ID}' AND effective_time >= now() - INTERVAL '${DAYS} days'
  ORDER BY effective_time DESC LIMIT 20;
"

echo "[verify] If you added liver views, you can peek:"
echo "services/healthdb-pg-0001/scripts/psql.sh -c \"SELECT * FROM analytics.v_liver_latest LIMIT 5;\""
echo "services/healthdb-pg-0001/scripts/psql.sh -c \"SELECT * FROM analytics.mv_liver_daily ORDER BY day DESC, person_id LIMIT 10;\""
