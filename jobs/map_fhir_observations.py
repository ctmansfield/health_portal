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

LOINC_NUMERIC = {
    "8867-4": "1/min",  # Heart rate
    "59408-5": "ratio",  # SpO2 (normalize to 0..1)
    "29463-7": "kg",  # Body weight
    "39156-5": "kg/m2",  # BMI
    "8480-6": "mm[Hg]",  # Systolic
    "8462-4": "mm[Hg]",  # Diastolic
}


def _emit(cur, dsn_rec):
    cur.execute(UPSERT_SQL, dsn_rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--person-id", default="me")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    # Pull observations that are either a direct numeric value or a BP panel with components
    sql = f"""
      SELECT id, effective_time, code_system, code, value_num, unit, resource
      FROM fhir_raw.v_observation_flat
      WHERE code_system = 'http://loinc.org'
        AND (
             code IN ('8867-4','59408-5','29463-7','39156-5','85354-9','8480-6','8462-4')
            )
      ORDER BY last_updated
      {('LIMIT %s' if args.limit else '')}
    """
    params = [args.limit] if args.limit else []

    inserted = updated = skipped = 0
    with pg(args.dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        for rid, ts, cs, code, val, unit, resource in cur.fetchall():
            if ts is None:
                skipped += 1
                continue

            # Normalize/expand
            to_emit = []
            if code == "59408-5" and val is not None:
                try:
                    v = float(val)
                    val = v / (100.0 if v > 1.5 else 1.0)
                except Exception:
                    skipped += 1
                    continue
                to_emit.append(
                    ("59408-5", float(val), unit or LOINC_NUMERIC["59408-5"])
                )
            elif code == "85354-9":
                # BP panel: look into components in raw resource
                try:
                    comps = resource.get("component") or []
                    for c in comps:
                        loinc = (((c.get("code") or {}).get("coding") or [{}])[0]).get(
                            "code"
                        )
                        if loinc in ("8480-6", "8462-4"):
                            q = c.get("valueQuantity") or {}
                            v = q.get("value")
                            if v is None:
                                continue
                            to_emit.append(
                                (loinc, float(v), q.get("unit") or LOINC_NUMERIC[loinc])
                            )
                except Exception:
                    skipped += 1
                    continue
            else:
                if val is None:
                    # might be a component-only observation; skip
                    skipped += 1
                    continue
                to_emit.append((code, float(val), unit or LOINC_NUMERIC.get(code, "")))

            for ccode, cval, cunit in to_emit:
                meta = json.dumps({"fhir_id": rid})
                rec = dict(
                    person_id=args.person_id,
                    source="fhir",
                    kind="Observation",
                    code_system="LOINC",
                    code=ccode,
                    value_num=cval,
                    unit=cunit,
                    effective_time=ts,
                    meta=meta,
                )
                try:
                    _emit(cur, rec)
                    if cur.rowcount == 1:
                        inserted += 1
                    else:
                        updated += 1
                except Exception:
                    conn.rollback()
                    skipped += 1
                else:
                    conn.commit()
    print(f"inserted={inserted} updated={updated} skipped={skipped}")


if __name__ == "__main__":
    main()
