#!/usr/bin/env python3
"""
Mirror FHIR Observation resources in fhir_raw.resources into analytics.data_events.
Idempotent; can run daily. Only processes Observations newer than state 'mirror_fhir_obs_last'.
"""
import argparse, json, datetime as dt
from hp_etl.db import pg
from hp_etl.events import bulk_insert
from hp_etl.state import get_state, set_state
from app.hp_etl.coding import normalize_system, normalize_unit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=None)
    ap.add_argument("--person-id", default="me")
    args = ap.parse_args()

    last = get_state("mirror_fhir_obs_last", args.dsn)
    with pg(args.dsn) as conn:
        q = """
        SELECT resource_id, resource
        FROM fhir_raw.resources
        WHERE resource_type='Observation'
          AND (
            (resource ? 'effectiveDateTime') OR (resource ? 'effectiveInstant')
          )
        """
        with conn.cursor() as cur:
            cur.execute(q)
            rows = cur.fetchall()

    out = []
    max_ts = last
    for rid, res in rows:
        r = res
        eff = r.get("effectiveDateTime") or r.get("effectiveInstant")
        if not eff:
            continue
        # e.g. '2025-09-09T12:00:00Z'
        if last and eff <= last:
            continue
        code = None
        system = None
        display = None
        coding = (r.get("code") or {}).get("coding") or []
        if coding:
            system = coding[0].get("system")
            code = coding[0].get("code")
            display = coding[0].get("display")
        val = None
        unit = None
        if "valueQuantity" in r:
            val = r["valueQuantity"].get("value")
            unit = r["valueQuantity"].get("unit")

        out.append(
            dict(
                person_id=args.person_id,
                source="ehr_fhir",
                kind="Observation",
                code_system=normalize_system(system) if system else None,
                code=code,
                display=display,
                effective_time=eff,
                effective_start=None,
                effective_end=None,
                value_num=val,
                value_text=None,
                unit=normalize_unit(unit) if unit else None,
                device_id=None,
                status=r.get("status"),
                raw=json.dumps(r),
                meta="{}",
            )
        )
        if (max_ts is None) or (eff > max_ts):
            max_ts = eff

    if out:
        bulk_insert(out, args.dsn)
    if max_ts:
        set_state("mirror_fhir_obs_last", max_ts, args.dsn)
        print("mirror_fhir_obs_last ->", max_ts)


if __name__ == "__main__":
    main()
