#!/usr/bin/env python3
import argparse
import sys
from hp_etl.db import pg, dsn_from_env
from hp_etl.exporters import to_csv, to_ndjson

SQL = """
SELECT person_id, day, hr_median, spo2_min
FROM analytics.mv_daily_vitals
WHERE (%(since)s IS NULL OR day >= %(since)s::date)
AND (%(person_id)s IS NULL OR person_id = %(person_id)s)
ORDER BY day DESC;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--since", default=None)
    ap.add_argument("--format", default="csv", choices=["csv", "ndjson"])
    ap.add_argument("--person-id", default=None)
    args = ap.parse_args()

    params = {"since": args.since, "person_id": args.person_id}

    with pg(args.dsn) as conn, conn.cursor() as cur:
        cur.execute(SQL, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        results = [dict(zip(columns, row)) for row in rows]

    if args.format == "csv":
        to_csv(results, sys.stdout, columns)
    else:
        to_ndjson(results, sys.stdout)


if __name__ == "__main__":
    main()
