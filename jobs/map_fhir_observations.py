#!/usr/bin/env python3
import argparse, json
from hp_etl.db import pg, dsn_from_env

UPSERT_SQL = """
INSERT INTO analytics.data_events
(person_id, source, kind, code_system, code, value_num, unit, effective_time, meta)
VALUES (%(person_id)s, %(source)s, %(kind)s, %(code_system)s, %(code)s, %(value_num)s, %(unit)s, %(effective_time)s, %(meta)s::jsonb)
ON CONFLICT ON CONSTRAINT uq_events_person_metric_time
DO UPDATE SET
  value_num = EXCLUDED.value_num,
  unit      = EXCLUDED.unit,
  meta      = COALESCE(analytics.data_events.meta, '{}'::jsonb) || EXCLUDED.meta;
"""

NUM_CODES = {
    "8867-4": "1/min",  # HR
    "59408-5": "ratio",  # SpO2 (0..1)
    "29463-7": "kg",  # Weight
    "39156-5": "kg/m2",  # BMI
    "8480-6": "mm[Hg]",  # SBP
    "8462-4": "mm[Hg]",  # DBP
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--person-id", default="me")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sql = f"""
      SELECT r.resource
      FROM fhir_raw.resources r
      WHERE r.resource_type='Observation'
      ORDER BY r.imported_at
      {('LIMIT %s' if args.limit else '')}
    """
    params = [args.limit] if args.limit else []

    inserted = updated = skipped = 0
    with pg(args.dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        for (res,) in cur.fetchall():
            if not isinstance(res, dict) or res.get("resourceType") != "Observation":
                skipped += 1
                continue

            eff = res.get("effectiveDateTime")
            code = (((res.get("code") or {}).get("coding") or []) or [{}])[0]
            c_system = (code.get("system") or "").lower()
            c_code = code.get("code")
            vq = res.get("valueQuantity") or {}
            comp = res.get("component") or []

            emissions = []

            # single numeric values
            if c_code in NUM_CODES and vq.get("value") is not None and eff:
                val = float(vq["value"])
                unit = vq.get("unit") or NUM_CODES[c_code]
                if c_code == "59408-5" and val > 1.5:  # normalize to 0..1
                    val = val / 100.0
                emissions.append((c_code, val, unit))

            # BP panel 85354-9 → components 8480-6 / 8462-4
            if c_code == "85354-9" and comp and eff:
                for part in comp:
                    pcode = (((part.get("code") or {}).get("coding") or []) or [{}])[
                        0
                    ].get("code")
                    pvq = part.get("valueQuantity") or {}
                    if pcode in ("8480-6", "8462-4") and pvq.get("value") is not None:
                        emissions.append(
                            (
                                pcode,
                                float(pvq["value"]),
                                (pvq.get("unit") or NUM_CODES[pcode]),
                            )
                        )

            if not emissions or not eff:
                skipped += 1
                continue

            for loinc, val, unit in emissions:
                rec = {
                    "person_id": args.person_id,
                    "source": "FHIR",
                    "kind": "observation",
                    "code_system": "LOINC" if "loinc" in c_system else c_system.upper(),
                    "code": loinc,
                    "value_num": val,
                    "unit": unit,
                    "effective_time": eff,
                    "meta": json.dumps(
                        {"obs_id": res.get("id"), "display": code.get("display")}
                    ),
                }
                cur.execute(UPSERT_SQL, rec)
                # psycopg3 rowcount is 1 for both insert & update; we won't distinguish here
                inserted += 1

    print(f"inserted={inserted} skipped={skipped}")


if __name__ == "__main__":
    main()
