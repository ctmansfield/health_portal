#!/usr/bin/env python3
import argparse, json, datetime as dt

try:
    from hp_etl.fhir_map import observation_to_event as _map_obs
except Exception:

    def _isoz(dtobj):
        return dtobj.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _map_obs(obs: dict):
        if obs.get("resourceType") != "Observation":
            return None
        code = (((obs.get("code") or {}).get("coding") or []) or [{}])[0]
        system = (code.get("system") or "").lower()
        c = code.get("code")
        vq = obs.get("valueQuantity") or {}
        v = vq.get("value")
        if c is None or v is None:
            return None
        # minimal normalization for HR & SpO2
        unit = (vq.get("unit") or "").strip()
        if c == "8867-4":  # Heart rate
            unit = "1/min"
        if c == "59408-5":  # SpO2 as fraction
            try:
                v = float(v) / (100.0 if float(v) > 1.5 else 1.0)
            except Exception:
                pass
            unit = "%"
        ts = (
            obs.get("effectiveDateTime")
            or obs.get("issued")
            or ((obs.get("meta") or {}).get("lastUpdated"))
            or _isoz(dt.datetime.utcnow())
        )
        return {
            "person_id": "me",
            "effective_time": ts,
            "code_system": (
                "LOINC" if "loinc.org" in system else (code.get("system") or system)
            ),
            "code": str(c),
            "value_num": float(v),
            "unit": unit or None,
            "meta": {"source": "fhir", "fallback": True},
        }


from hp_etl.db import pg, dsn_from_env

UPSERT_SQL = """
INSERT INTO analytics.data_events
(person_id, effective_time, code_system, code, value_num, unit, meta)
VALUES (%(person_id)s, %(effective_time)s, %(code_system)s, %(code)s, %(value_num)s, %(unit)s, %(meta)s::jsonb)
ON CONFLICT ON CONSTRAINT uq_events_person_metric_time
DO UPDATE SET
  value_num = EXCLUDED.value_num,
  unit      = EXCLUDED.unit,
  meta      = COALESCE(analytics.data_events.meta, '{}'::jsonb) || EXCLUDED.meta;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    ap.add_argument(
        "--since", default=None, help="ISO; only fhir_raw.imported_at >= since"
    )
    ap.add_argument("--person-id", default="me")
    args = ap.parse_args()

    where = ["resource_type = 'Observation'"]
    params = []
    if args.since:
        where.append("imported_at >= %s")
        params.append(args.since)
    sql = f"""
      SELECT resource
      FROM fhir_raw.resources
      WHERE {' AND '.join(where)}
      ORDER BY imported_at ASC
      {('LIMIT %s' if args.limit else '')}
    """
    if args.limit:
        params.append(args.limit)

    inserted = skipped = 0
    with pg(args.dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        for (res,) in cur.fetchall():
            evt = _map_obs(res)
            if not evt:
                skipped += 1
                continue
            evt["person_id"] = args.person_id
            evt["meta"] = json.dumps(
                {**(evt.get("meta") or {}), "mapper": "fhir-map-0002"},
                separators=(",", ":"),
            )
            try:
                cur.execute(UPSERT_SQL, evt)
                inserted += 1
            except Exception:
                skipped += 1
        conn.commit()
    print(f"Done. upserts={inserted}; skipped={skipped}")


if __name__ == "__main__":
    main()
