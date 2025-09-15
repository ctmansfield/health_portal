#!/usr/bin/env python3
import argparse
import sys
from hp_etl.db import pg, dsn_from_env
from hp_etl.exporters import to_csv, to_ndjson

SQL = """
SELECT person_id, day, hr_median, spo2_min
FROM analytics.mv_daily_vitals
WHERE (%(since)s IS NULL OR day >= %(since)s::date)
ORDER BY day DESC
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--since", default=None)
    ap.add_argument("--format", choices=["csv", "ndjson"], default="csv")
    args = ap.parse_args()

    with pg(args.dsn) as conn, conn.cursor() as cur:
        cur.execute(SQL, {"since": args.since})
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    if args.format == "csv":
        from io import StringIO

        sio = StringIO()
        to_csv(rows, sio, cols)
        sys.stdout.write(sio.getvalue())
    else:
        to_ndjson(rows, sys.stdout)


if __name__ == "__main__":
    main()
