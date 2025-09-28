#!/usr/bin/env python3
"""
load_mdjson_to_db.py

Reads NDJSON produced by normalize_to_mdjson.py and loads into
analytics.lab_ingest_raw_mdjson, then runs analytics.load_data_events_new_from_mdjson()
which populates analytics.data_events_new.

Usage:
  export HP_PG_DSN=postgresql://user:pass@host:port/db
  python tools/portal_ingest/load_mdjson_to_db.py --ndjson out.ndjson [--source portal --note "portal backfill"]
"""
import argparse
import json
import os
import sys
import psycopg
from psycopg.rows import dict_row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ndjson", required=True, help="Path to NDJSON from normalize_to_mdjson.py")
    ap.add_argument("--dsn", default=os.getenv("HP_PG_DSN"), help="Postgres DSN (default HP_PG_DSN)")
    ap.add_argument("--source", default=None, help="Override staging source column")
    ap.add_argument("--note", default=None, help="Optional note saved with staging rows")
    args = ap.parse_args()

    if not args.dsn:
        print("ERROR: --dsn or HP_PG_DSN is required", file=sys.stderr)
        sys.exit(2)

    rows = []
    with open(args.ndjson, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception as e:
                print(f"[skip] bad json: {e}", file=sys.stderr)
                continue
            rows.append(payload)

    with psycopg.connect(args.dsn) as conn:
        with conn.cursor() as cur:
            # Insert into staging
            for p in rows:
                cur.execute(
                    """
                    INSERT INTO analytics.lab_ingest_raw_mdjson (person_id, payload, source, note)
                    VALUES (%s, %s::jsonb, COALESCE(%s, %s), %s)
                    """,
                    (
                        p.get("person_id"),
                        json.dumps(p),
                        args.source,
                        p.get("source"),
                        args.note,
                    ),
                )
        conn.commit()
        # Transform into data_events_new
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT analytics.load_data_events_new_from_mdjson() AS inserted")
            n = cur.fetchone()["inserted"]
        print({"inserted": n})


if __name__ == "__main__":
    main()
