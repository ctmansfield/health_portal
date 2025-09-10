#!/usr/bin/env python3
"""
Map FHIR Observation resources into analytics.data_events.
Supports only LOINC 8867-4 (HR) and 59408-5 (SpO2).

Usage: python jobs/map_fhir_to_events.py --dsn <DSN> [--person-id me]
"""
import argparse
import json
import datetime as dt
from hp_etl.db import pg

LOINC_HR = "8867-4"
LOINC_SPO2 = "59408-5"

SQL_SELECT = """
SELECT resource
FROM fhir_raw.resources
WHERE resource_type='Observation'
"""

SQL_UPSERT = """
INSERT INTO analytics.data_events
  (person_id, source, kind, code_system, code, display, effective_time,
   value_num, unit, meta)
VALUES (%(person_id)s, 'ehr_fhir', 'Observation', 'LOINC', %(code)s, %(display)s, %(effective_time)s,
        %(value_num)s, %(unit)s, %(meta)s::jsonb)
ON CONFLICT ON CONSTRAINT uq_events_person_metric_time
DO UPDATE SET
  value_num = EXCLUDED.value_num,
  unit = EXCLUDED.unit,
  meta = EXCLUDED.meta
WHERE analytics.data_events.value_num IS DISTINCT FROM EXCLUDED.value_num
"""


def normalize_hr(value, unit):
    # Accept bpm, /min, 1/min, return value unchanged, unit "1/min"
    # No conversion
    return value, "1/min"


def normalize_spo2(value, unit):
    # If value > 1.5 assume percent; convert to ratio
    if value > 1.5:
        value = value / 100.0
    return value, "ratio"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    ap.add_argument("--person-id", default="me")
    args = ap.parse_args()

    with pg(args.dsn) as conn:
        cur = conn.cursor()
        cur.execute(SQL_SELECT)
        rows = cur.fetchall()

    batch = []
    for (res_json,) in rows:
        obs = res_json
        if not isinstance(obs, dict):
            continue
        code = None
        display = None
        # Find LOINC code in obs.code.coding[0]
        codings = (obs.get("code") or {}).get("coding") or []
        if not codings:
            continue
        c0 = codings[0]
        if c0.get("system", "").lower().endswith("loinc.org"):
            code = c0.get("code")
            display = c0.get("display")
        if code not in (LOINC_HR, LOINC_SPO2):
            continue

        # Get numeric valueQuantity.value
        qv = obs.get("valueQuantity")
        if not qv:
            continue
        val = qv.get("value")
        if not isinstance(val, (int, float)):
            continue
        unit_in = qv.get("unit")

        # Extract effective_time
        effective_time = obs.get("effectiveDateTime") or obs.get("issued")
        if not effective_time:
            continue

        # Normalize based on code
        if code == LOINC_HR:
            val, unit = normalize_hr(val, unit_in)
        else:
            val, unit = normalize_spo2(val, unit_in)

        meta = {"source": "fhir", "obs_id": obs.get("id")}
        cat = obs.get("category") or []
        if cat and isinstance(cat, list) and cat[0].get("coding") and cat[0]["coding"]:
            meta["category_code"] = cat[0]["coding"][0].get("code")

        row = dict(
            person_id=args.person_id,
            code=code,
            display=display,
            effective_time=effective_time,
            value_num=val,
            unit=unit,
            meta=json.dumps(meta),
        )

        batch.append(row)

    with pg(args.dsn) as conn:
        cur = conn.cursor()
        for r in batch:
            cur.execute(SQL_UPSERT, r)
        conn.commit()


if __name__ == "__main__":
    main()
