#!/usr/bin/env python3
import json
import os
import sys
import datetime as dt
from typing import Any, Dict
import psycopg

PG_DSN = (
    os.environ.get("PG_DSN")
    or "host=localhost port=5432 dbname=health_portal user=postgres"
)


def parse_iso(ts: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)


def insert_lab(conn, rec: Dict[str, Any]):
    conn.execute(
        """
      INSERT INTO clinical.lab_result(
        person_id, panel_id, loinc_code, test_name, value_num, value_text, unit,
        observed_at, status, interpretation, ref_low, ref_high, raw_json)
      VALUES (%(person_id)s,%(panel_id)s,%(loinc_code)s,%(test_name)s,%(value_num)s,
              %(value_text)s,%(unit)s,%(observed_at)s,%(status)s,%(interpretation)s,
              %(ref_low)s,%(ref_high)s,%(raw_json)s)""",
        rec,
    )


def mirror_obs(conn, person_id: str, metric: str, ts: dt.datetime, val, raw: str):
    conn.execute(
        """INSERT INTO analytics.observation_flat(person_id,metric,t_utc,value_num,raw_json)
                    VALUES (%s,%s,%s,%s,%s)""",
        (person_id, metric, ts, val, raw),
    )


def ingest_bundle(bundle: Dict[str, Any], default_person: str | None = None):
    with psycopg.connect(PG_DSN, autocommit=True) as conn:
        for e in bundle.get("entry", []):
            res = e.get("resource", {})
            rt = res.get("resourceType")
            if rt == "Observation":
                coding = (res.get("code", {}).get("coding", []) or [{}])[0]
                loinc = coding.get("code")
                test = (
                    coding.get("display")
                    or res.get("code", {}).get("text")
                    or "Observation"
                )
                q = res.get("valueQuantity") or {}
                val = q.get("value")
                unit = q.get("unit")
                ts = parse_iso(
                    res.get("effectiveDateTime")
                    or res.get("issued")
                    or dt.datetime.utcnow().isoformat()
                )
                person = default_person or (
                    res.get("subject", {}).get("reference") or "unknown"
                )
                raw = json.dumps(res)
                rec = dict(
                    person_id=person,
                    panel_id=None,
                    loinc_code=loinc,
                    test_name=test,
                    value_num=val,
                    value_text=None,
                    unit=unit,
                    observed_at=ts,
                    status=res.get("status"),
                    interpretation=None,
                    ref_low=None,
                    ref_high=None,
                    raw_json=raw,
                )
                insert_lab(conn, rec)
                metric = (test or "").lower().replace(" ", "_")
                if isinstance(val, (int, float)) or (
                    isinstance(val, str) and val.replace(".", "", 1).isdigit()
                ):
                    mirror_obs(conn, person, metric, ts, val, raw)

            elif rt == "DocumentReference":
                conn.execute(
                    """INSERT INTO clinical.clinical_note(person_id,note_type,authored_at,title,text,raw_json)
                                VALUES (%s,%s,%s,%s,%s,%s)""",
                    (
                        default_person or "unknown",
                        "document",
                        parse_iso(res.get("date") or dt.datetime.utcnow().isoformat()),
                        res.get("description") or res.get("type", {}).get("text"),
                        (res.get("content", [{}])[0].get("attachment", {}) or {}).get(
                            "title"
                        ),
                        json.dumps(res),
                    ),
                )

            elif rt == "ImagingStudy":
                conn.execute(
                    """INSERT INTO imaging.imaging_study(person_id,study_uid,modality,started_at,description,raw_json)
                                VALUES (%s,%s,%s,%s,%s,%s)
                                ON CONFLICT (study_uid) DO NOTHING""",
                    (
                        default_person or "unknown",
                        res.get("uid")
                        or (res.get("identifier", [{}])[0] or {}).get("value"),
                        (res.get("modalities", [{}])[0] or {}).get("code"),
                        parse_iso(
                            res.get("started") or dt.datetime.utcnow().isoformat()
                        ),
                        res.get("description"),
                        json.dumps(res),
                    ),
                )


def main():
    if len(sys.argv) < 2:
        print("usage: fhir_import.py <bundle.json> [person_id]", file=sys.stderr)
        sys.exit(1)
    bundle = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    ingest_bundle(bundle, default_person=(sys.argv[2] if len(sys.argv) > 2 else None))
    print("[ok] bundle ingested")


if __name__ == "__main__":
    main()
