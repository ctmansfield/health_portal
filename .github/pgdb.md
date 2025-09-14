Where the data lives (current map)

Schemas

fhir_raw

Table: fhir_raw.resources (raw FHIR JSON; NDJSON imports land here)

Views:

fhir_raw.v_observation_flat (Observation → flattened columns)

fhir_raw.v_observation_counts (quick counts of Observations by code)

analytics

Core table: analytics.data_events
Unified metric stream (person_id, code_system, code, value_num, unit, effective_time, meta)

Views/MVs you already have:

analytics.v_events_recent

analytics.mv_events_daily

analytics.mv_vitals_daily_wide

analytics.mv_weight_daily

analytics.v_vitals_latest

analytics.v_bp_latest

analytics.anomaly_thresholds

analytics.v_vitals_anomalies

(optional) analytics.ai_findings if present in your build

Quick inventory commands (safe to run)
# list schemas
services/healthdb-pg-0001/scripts/psql.sh -c "\dn"

# relations in fhir_raw
services/healthdb-pg-0001/scripts/psql.sh -c "\dt fhir_raw.*"
services/healthdb-pg-0001/scripts/psql.sh -c "\dv fhir_raw.*"

# relations in analytics
services/healthdb-pg-0001/scripts/psql.sh -c "\dt analytics.*"
services/healthdb-pg-0001/scripts/psql.sh -c "\dv analytics.*"

# confirm anomaly thresholds + anomalies view
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT * FROM analytics.anomaly_thresholds ORDER BY code;"
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT * FROM analytics.v_vitals_anomalies LIMIT 10;"

Discover liver-related codes already present in your data

Run these first to see what you actually have before we create any liver views:

# Liver-ish strings in Observation display text
services/healthdb-pg-0001/scripts/psql.sh -A -F '|' -t -c "
  SELECT code_system, code, COUNT(*) AS n, MIN(last_updated), MAX(last_updated)
  FROM fhir_raw.v_observation_flat
  WHERE lower(display) ~ '(alt|ast|bilirubin|alkaline|ggt|gamma|albumin|liver)'
     OR code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
  GROUP BY 1,2 ORDER BY n DESC;
"

# What’s already mapped into analytics.data_events by LOINC code?
services/healthdb-pg-0001/scripts/psql.sh -A -F '|' -t -c "
  SELECT code, COUNT(*) AS n, MIN(effective_time), MAX(effective_time)
  FROM analytics.data_events
  WHERE code_system='LOINC'
    AND code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
  GROUP BY 1 ORDER BY n DESC;
"


Notes on the codes above (verify in your data):

ALT (Alanine aminotransferase): 1742-6

AST (Aspartate aminotransferase): 1920-8

Alkaline phosphatase: 6768-6

GGT: 2324-2

Bilirubin, total: 1975-2

Bilirubin, direct: 1968-7

Albumin (serum): 1751-7
If your counts query shows different codes in use, swap them into the views below.

Drop-in: “latest liver labs” view + “daily liver labs” MV

Paste these exactly (adjust code list if your discovery query found different codes):

-- services/healthdb-pg-0001/init/054_liver_views.sql
-- Latest liver labs per person (most recent per code pivoted to columns)
CREATE OR REPLACE VIEW analytics.v_liver_latest AS
WITH ranked AS (
  SELECT
    person_id, code, value_num, unit, effective_time,
    ROW_NUMBER() OVER (PARTITION BY person_id, code ORDER BY effective_time DESC) AS rn
  FROM analytics.data_events
  WHERE code_system='LOINC'
    AND code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
)
SELECT
  person_id,
  MAX(CASE WHEN code='1742-6' THEN value_num END) FILTER (WHERE rn=1) AS alt_uL,
  MAX(CASE WHEN code='1920-8' THEN value_num END) FILTER (WHERE rn=1) AS ast_uL,
  MAX(CASE WHEN code='6768-6' THEN value_num END) FILTER (WHERE rn=1) AS alp_uL,
  MAX(CASE WHEN code='2324-2' THEN value_num END) FILTER (WHERE rn=1) AS ggt_uL,
  MAX(CASE WHEN code='1975-2' THEN value_num END) FILTER (WHERE rn=1) AS bili_total_mgdl,
  MAX(CASE WHEN code='1968-7' THEN value_num END) FILTER (WHERE rn=1) AS bili_direct_mgdl,
  MAX(CASE WHEN code='1751-7' THEN value_num END) FILTER (WHERE rn=1) AS albumin_gdl,
  MAX(effective_time) FILTER (WHERE rn=1) AS updated_at
FROM ranked
GROUP BY person_id
ORDER BY updated_at DESC NULLS LAST;

-- Daily medians (or mins for bilirubin) per person/day for liver labs
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_liver_daily AS
SELECT
  person_id,
  (effective_time AT TIME ZONE 'UTC')::date AS day,
  -- choose aggregation suitable for each lab (you can change these)
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='1742-6' THEN value_num END) AS alt_p50,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='1920-8' THEN value_num END) AS ast_p50,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='6768-6' THEN value_num END) AS alp_p50,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='2324-2' THEN value_num END) AS ggt_p50,
  MAX(CASE WHEN code='1975-2' THEN value_num END) AS bili_total_max,    -- often tracked as a max in a day
  MAX(CASE WHEN code='1968-7' THEN value_num END) AS bili_direct_max,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY CASE WHEN code='1751-7' THEN value_num END) AS albumin_p50
FROM analytics.data_events
WHERE code_system='LOINC'
  AND code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7')
  AND value_num IS NOT NULL
GROUP BY 1,2
ORDER BY day DESC;

CREATE INDEX IF NOT EXISTS idx_mv_liver_daily_day ON analytics.mv_liver_daily(day);


Apply & peek:

services/healthdb-pg-0001/scripts/psql.sh < services/healthdb-pg-0001/init/054_liver_views.sql
services/healthdb-pg-0001/scripts/psql.sh -c "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_liver_daily" \
  || services/healthdb-pg-0001/scripts/psql.sh -c "REFRESH MATERIALIZED VIEW analytics.mv_liver_daily"

# quick checks
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT * FROM analytics.v_liver_latest LIMIT 5;"
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT * FROM analytics.mv_liver_daily ORDER BY day DESC, person_id LIMIT 10;"

(Optional) Add liver codes to the anomaly thresholds

If you want these to show up in /api/anomalies/vitals automatically:

-- services/healthdb-pg-0001/init/055_liver_thresholds.sql
INSERT INTO analytics.anomaly_thresholds (code, min_val, max_val, reason, enabled)
VALUES
  ('1742-6', 0, 55,  'ALT high', TRUE),
  ('1920-8', 0, 40,  'AST high', TRUE),
  ('6768-6', 30, 120,'ALP out of range', TRUE),
  ('2324-2', 0, 60,  'GGT high', TRUE),
  ('1975-2', 0, 1.3, 'Bilirubin total high', TRUE),
  ('1968-7', 0, 0.3, 'Bilirubin direct high', TRUE),
  ('1751-7', 3.2, 5.0, 'Albumin low/high', TRUE)
ON CONFLICT (code) DO NOTHING;


Apply & verify:

services/healthdb-pg-0001/scripts/psql.sh < services/healthdb-pg-0001/init/055_liver_thresholds.sql
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT * FROM analytics.anomaly_thresholds WHERE code IN ('1742-6','1920-8','6768-6','2324-2','1975-2','1968-7','1751-7') ORDER BY code;"

API (optional) – tiny router to expose liver data

If you want a clean API surface for the frontend (skip if you prefer SQL-only):

# app/api/routers/liver.py
from fastapi import APIRouter, Query
from typing import Optional, Any, Dict, List
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["liver"])

@router.get("/liver/latest")
def liver_latest() -> Dict[str, Any]:
    sql = """
      SELECT person_id, alt_uL, ast_uL, alp_uL, ggt_uL, bili_total_mgdl, bili_direct_mgdl, albumin_gdl, updated_at
      FROM analytics.v_liver_latest
      ORDER BY updated_at DESC NULLS LAST
    """
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return {"rows": [dict(zip(cols, r)) for r in cur.fetchall()]}

@router.get("/liver/daily")
def liver_daily(days: int = Query(90, ge=1, le=365), person_id: Optional[str] = None) -> Dict[str, Any]:
    where = ["day >= current_date - %s::int"]
    params: List[Any] = [days]
    if person_id:
        where.append("person_id = %s"); params.append(person_id)
    sql = f"""
      SELECT person_id, day, alt_p50, ast_p50, alp_p50, ggt_p50, bili_total_max, bili_direct_max, albumin_p50
      FROM analytics.mv_liver_daily
      WHERE {' AND '.join(where)}
      ORDER BY day DESC, person_id
    """
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return {"rows": [dict(zip(cols, r)) for r in cur.fetchall()]}


Wire it up (only once):

# import & include in app/api/main.py
grep -q "from \.routers\.liver import router as liver_router" app/api/main.py || \
  sed -i '1 a from .routers.liver import router as liver_router' app/api/main.py

grep -q 'app.include_router(liver_router, prefix="/api")' app/api/main.py || \
  awk '/include_router\(summary_router/{print; print "app.include_router(liver_router, prefix=\"/api\")"; next}1' \
  app/api/main.py > /tmp/main.$$ && mv /tmp/main.$$ app/api/main.py

# smoke test (port as you used before)
curl -s "http://127.0.0.1:8810/api/liver/latest" | jq .
curl -s "http://127.0.0.1:8810/api/liver/daily?days=30" | jq .

Other “critical” monitors you likely want next

(Use the same discovery → codify pattern)

Renal: Creatinine, eGFR, BUN

Electrolytes: Potassium, Sodium, CO₂ (bicarb), Chloride

Glucose: fasting glucose, HbA1c

Hematology: Hemoglobin/Hematocrit, Platelets, WBC

Cardiac: High-sensitivity Troponin (if present)

Coag: INR / PT (if present)

I can provide matching “latest” + “daily” views for each set once you confirm which codes actually appear in your v_observation_counts output.

Commit summary (when you check this in)

feat(liver): add liver lab views (latest + daily), thresholds, and optional API

analytics.v_liver_latest and analytics.mv_liver_daily

seed anomaly thresholds for ALT/AST/ALP/GGT/bilirubin/albumin

optional router /api/liver/latest and /api/liver/daily for frontend consumption
