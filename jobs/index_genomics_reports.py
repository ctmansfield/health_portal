#!/usr/bin/env python3
"""
Index genomics risk report files into analytics.genomics_reports.
- Looks in GEN_REPORT_DIR (env or default) for files (pdf/html).
- Extracts report_id (filename), optional person_id (from filename pattern), and inserts/updates the table.
"""

import os
import argparse
import json
import datetime as dt
from hp_etl.db import pg

DEFAULT_DIR = "/mnt/nas_storage/genomics-stack/risk_reports/out"

SQL_UPSERT = """
INSERT INTO analytics.genomics_reports(report_id, person_id, filename, path, generated_at, summary)
VALUES (%s,%s,%s,%s,%s,%s::jsonb)
ON CONFLICT (report_id) DO UPDATE SET path=EXCLUDED.path, filename=EXCLUDED.filename, generated_at=EXCLUDED.generated_at, summary=EXCLUDED.summary
"""


def guess_person_id(filename: str) -> str | None:
    # naive heuristic: file may be <person_id>_report.pdf or contain patient_<id>
    bn = os.path.basename(filename)
    parts = bn.split("_")
    if parts:
        maybe = parts[0]
        if maybe.isalnum() and len(maybe) >= 3:
            return maybe
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.environ.get("GEN_REPORT_DIR", DEFAULT_DIR))
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()

    files = []
    for fn in sorted(os.listdir(args.dir)):
        path = os.path.join(args.dir, fn)
        if not os.path.isfile(path):
            continue
        files.append((fn, path))

    with pg(args.dsn) as conn:
        cur = conn.cursor()
        for fn, path in files:
            report_id = fn
            person_id = guess_person_id(fn)
            # generated_at from mtime
            generated_at = (
                dt.datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat() + "Z"
            )
            summary = json.dumps({})
            cur.execute(
                SQL_UPSERT, (report_id, person_id, fn, path, generated_at, summary)
            )
        conn.commit()


if __name__ == "__main__":
    main()
