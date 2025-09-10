#!/usr/bin/env python3
"""Seed sample data for dashboard development.
- Inserts a few analytics.data_events rows for person_id 'me' suitable for HR & SpO2 materialized views.
- Optionally refreshes materialized views (requires hp_dsn set and views exist).
"""
import argparse, datetime as dt, json
from app.hp_etl.db import pg, dsn_from_env

SQL_INSERT = """
INSERT INTO analytics.data_events
  (person_id, source, kind, code_system, code, display, effective_time, value_num, unit, meta)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
ON CONFLICT ON CONSTRAINT uq_events_person_metric_time
DO UPDATE SET value_num = EXCLUDED.value_num, unit = EXCLUDED.unit, meta = EXCLUDED.meta
"""

LOINC_HR = "8867-4"
LOINC_SPO2 = "59408-5"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--person-id", default="me")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument(
        "--genomics", action="store_true", help="seed genomics_reports table"
    )
    ap.add_argument("--findings", action="store_true", help="seed ai_findings")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    # create HR & SPO2 values for each day
    for i in range(args.days):
        day = now - dt.timedelta(days=i)
        # times within day
        t1 = (day - dt.timedelta(hours=6)).isoformat()
        t2 = (day - dt.timedelta(hours=12)).isoformat()
        hr_val = 60 + (i % 5) * 2 + (i % 3)
        spo2_val = 0.95 + ((i % 4) * 0.002)
        rows.append(
            (
                args.person_id,
                "sim",
                "Observation",
                "LOINC",
                LOINC_HR,
                "Heart rate",
                t1,
                hr_val,
                "1/min",
                json.dumps({"sample": True}),
            )
        )
        rows.append(
            (
                args.person_id,
                "sim",
                "Observation",
                "LOINC",
                LOINC_SPO2,
                "SpO2",
                t2,
                spo2_val,
                "%",
                json.dumps({"sample": True}),
            )
        )

    inserted = 0
    with pg(args.dsn) as conn:
        cur = conn.cursor()
        for r in rows:
            try:
                cur.execute(SQL_INSERT, r)
                inserted += 1
            except Exception as e:
                print("insert failed", e)
        conn.commit()
    print(
        f"Inserted {inserted} sample events for person {args.person_id} into analytics.data_events"
    )

    # optional: seed genomics_reports
    if args.genomics:
        sample_reports = []
        for i in range(min(10, args.days)):
            rid = f"rpt_{i}"
            fn = f"report_{i}.pdf"
            path = f"/tmp/{fn}"
            gen_at = (now - dt.timedelta(days=i)).isoformat().replace("+00:00", "Z")
            summary = json.dumps({"notes": f"sample report {i}"})
            sample_reports.append((rid, args.person_id, fn, path, gen_at, summary))
        with pg(args.dsn) as conn:
            cur = conn.cursor()
            for rpt in sample_reports:
                try:
                    cur.execute(
                        "INSERT INTO analytics.genomics_reports(report_id, person_id, filename, path, generated_at, summary) VALUES (%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT (report_id) DO UPDATE SET path=EXCLUDED.path, filename=EXCLUDED.filename, generated_at=EXCLUDED.generated_at, summary=EXCLUDED.summary",
                        rpt,
                    )
                except Exception as e:
                    print("genomics insert failed", e)
            conn.commit()
        print(f"Inserted {len(sample_reports)} sample genomics_reports")

    # optional: seed ai_findings
    if args.findings:
        findings = []
        for i in range(min(14, args.days)):
            ft = (now - dt.timedelta(days=i)).date().isoformat() + "T00:00:00Z"
            findings.append(
                (
                    args.person_id,
                    ft,
                    "hr",
                    "zscore",
                    float((i % 5) - 2),
                    "info",
                    json.dumps({"n": 7}),
                    json.dumps({"ctx": "sample"}),
                )
            )
        with pg(args.dsn) as conn:
            cur = conn.cursor()
            for frow in findings:
                try:
                    cur.execute(
                        'INSERT INTO analytics.ai_findings (person_id, finding_time, metric, method, score, level, "window", context) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT (person_id, finding_time, metric) DO NOTHING',
                        frow,
                    )
                except Exception as e:
                    print("finding insert failed", e)
            conn.commit()
        print(f"Inserted {len(findings)} sample ai_findings")

    # attempt to refresh materialized views (best-effort)
    try:
        from jobs.refresh_materialized_views import main as refresh_main

        print("Refreshing materialized views (best-effort)")
        refresh_main()
    except Exception as e:
        print("Could not refresh materialized views automatically:", e)


if __name__ == "__main__":
    main()
