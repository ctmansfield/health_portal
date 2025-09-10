#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "[1/4] docker compose ps"
docker compose ps

echo "[2/4] wait for postgres readiness"
for i in $(seq 1 40); do
  if docker compose exec -T db pg_isready -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}" >/dev/null 2>&1; then
    echo " - ready"
    break
  fi
  sleep 1
done

echo "[3/4] schemas"
docker compose exec -T db psql -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}" -c "\dn+"
docker compose exec -T db psql -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}" -c "\dt fhir_raw.*"
docker compose exec -T db psql -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}" -c "\dt analytics.*"

echo "[4/4] smoke inserts"
docker compose exec -T db psql -U "${POSTGRES_USER:-health}" -d "${POSTGRES_DB:-health}" <<'SQL'
INSERT INTO fhir_raw.resources(resource_type,resource_id,resource)
VALUES('Observation','verify-obs-1',
'{"status":"final","code":{"coding":[{"system":"http://loinc.org","code":"8867-4","display":"Heart rate"}]},"valueQuantity":{"value":72,"unit":"beats/min"},"effectiveDateTime":"2025-09-09T12:00:00Z"}')
ON CONFLICT (resource_type,resource_id) DO UPDATE SET imported_at=now();

INSERT INTO analytics.data_events(person_id,source,kind,code_system,code,display,effective_time,value_num,unit,raw)
VALUES('me','apple_health','Observation','LOINC','8867-4','Heart rate','2025-09-09T12:00:00Z',72,'beats/min','{"origin":"verify"}');

SELECT count(*) AS fhir_count FROM fhir_raw.resources;
SELECT count(*) AS events_count FROM analytics.data_events;
SQL

echo "[✓] verify ok"
