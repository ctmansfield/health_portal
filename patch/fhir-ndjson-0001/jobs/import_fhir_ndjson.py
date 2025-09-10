#!/usr/bin/env python3
import argparse, json, gzip
from typing import IO
from hp_etl.db import pg, dsn_from_env

SQL = """
INSERT INTO fhir_raw.resources(resource_type, resource_id, resource)
VALUES (%s,%s,%s::jsonb)
ON CONFLICT (resource_type, resource_id) DO UPDATE
  SET resource=EXCLUDED.resource, imported_at=now();
"""


def opener(path: str) -> IO[bytes]:
    return gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)  # .ndjson or .ndjson.gz
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--batch-size", type=int, default=1000)
    ap.add_argument("--since", default=None)  # ISO; skip if meta.lastUpdated < since
    args = ap.parse_args()

    inserted = 0
    skipped = 0
    batch = []
    with opener(args.file) as f:
        for bline in f:
            try:
                obj = json.loads(bline.decode("utf-8"))
            except Exception:
                skipped += 1
                continue
            rtype = obj.get("resourceType")
            rid = obj.get("id")
            if not rtype or not rid:
                skipped += 1
                continue
            if args.since:
                lu = (obj.get("meta") or {}).get("lastUpdated")
                if lu and lu < args.since:
                    skipped += 1
                    continue
            batch.append((rtype, rid, json.dumps(obj)))
            if len(batch) >= args.batch_size:
                with pg(args.dsn) as conn, conn.cursor() as cur:
                    cur.executemany(SQL, batch)
                inserted += len(batch)
                batch.clear()
        if batch:
            with pg(args.dsn) as conn, conn.cursor() as cur:
                cur.executemany(SQL, batch)
            inserted += len(batch)
    print(f"Inserted {inserted}; Skipped {skipped}")


if __name__ == "__main__":
    main()
