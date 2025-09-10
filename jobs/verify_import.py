#!/usr/bin/env python3
import json
from hp_etl.db import pg, dsn_from_env

EXPECT = {
    "AllergyIntolerance": 1,
    "Condition": 11,
    "DocumentReference": 8,
    "Immunization": 7,
    "MedicationStatement": 6,
    "Observation": 214,
    "Organization": 1,
    "Patient": 1,
    "Practitioner": 1,
    "_total": 250,
}


def one(sql, params=None):
    with pg(dsn_from_env()) as conn, conn.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchone()


def many(sql, params=None):
    with pg(dsn_from_env()) as conn, conn.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    res_counts = many(
        "SELECT resource_type, COUNT(*) AS n FROM fhir_raw.resources GROUP BY 1 ORDER BY 1;"
    )
    total = sum(int(r["n"]) for r in res_counts)
    mismatches = []
    for r in res_counts:
        exp = EXPECT.get(r["resource_type"])
        if exp is not None and int(r["n"]) != exp:
            mismatches.append(
                {"resource": r["resource_type"], "expected": exp, "actual": int(r["n"])}
            )
    if total != EXPECT["_total"]:
        mismatches.append(
            {"resource": "_total", "expected": EXPECT["_total"], "actual": total}
        )

    obs_range = one(
        """
      WITH flat AS (
        SELECT (resource->>'effectiveDateTime')::timestamptz AS effective_time
        FROM fhir_raw.resources WHERE resource_type='Observation'
      )
      SELECT MIN(effective_time), MAX(effective_time), COUNT(*) FROM flat;
    """
    )

    events_summary = one(
        "SELECT MIN(effective_time), MAX(effective_time), COUNT(*) FROM analytics.data_events;"
    )
    dup_count = one(
        """
      SELECT COALESCE(SUM(c-1),0) FROM (
        SELECT COUNT(*) AS c
        FROM analytics.data_events
        GROUP BY person_id, code_system, code, effective_time
        HAVING COUNT(*)>1
      ) s;
    """
    )[0]

    out = {
        "counts": res_counts,
        "expected_mismatches": mismatches,
        "observation": {"min": obs_range[0], "max": obs_range[1], "n": obs_range[2]},
        "events": {
            "min": events_summary[0],
            "max": events_summary[1],
            "n": events_summary[2],
            "duplicates": int(dup_count or 0),
        },
        "views": {
            "v_vitals_latest": many("SELECT * FROM analytics.v_vitals_latest LIMIT 3;"),
            "v_bp_latest": many("SELECT * FROM analytics.v_bp_latest LIMIT 3;"),
        },
    }
    print(json.dumps(out, default=str, indent=2))


if __name__ == "__main__":
    main()
