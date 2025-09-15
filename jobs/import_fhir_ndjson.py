#!/usr/bin/env python3
import argparse
import json
import gzip
from typing import IO
from hp_etl.db import pg, dsn_from_env


def opener(path: str) -> IO[bytes]:
    return gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")


INSERT_SQL = """
INSERT INTO fhir_raw.resources (resource_type, resource)
VALUES (%(rt)s, %(res)s::jsonb)
ON CONFLICT (resource_type, (resource->>'id')) DO NOTHING
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--file", required=True)
    ap.add_argument(
        "--type", help="optional resourceType override (auto-detect if absent)"
    )
    args = ap.parse_args()

    inserted = skipped = bad = 0
    with opener(args.file) as fh, pg(args.dsn) as conn, conn.cursor() as cur:
        for i, raw in enumerate(fh, start=1):
            try:
                obj = json.loads(raw.decode("utf-8"))
            except Exception:
                bad += 1
                continue
            rt = args.type or obj.get("resourceType")
            rid = obj.get("id")
            if not rt or not rid:
                bad += 1
                continue
            cur.execute(INSERT_SQL, {"rt": rt, "res": json.dumps(obj)})
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
            if i % 1000 == 0:
                conn.commit()
        conn.commit()
    print(f"Inserted {inserted}; Skipped {skipped}; Bad {bad}")


if __name__ == "__main__":
    main()
