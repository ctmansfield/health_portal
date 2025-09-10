#!/usr/bin/env python3
from hp_etl.db import pg, dsn_from_env

SQL_BY_TYPE = """
SELECT resource->>'id' AS id, COUNT(*) AS n, MIN(imported_at) AS first_seen, MAX(imported_at) AS last_seen
FROM fhir_raw.resources
WHERE resource_type = %s
GROUP BY 1
ORDER BY n DESC, last_seen DESC;
"""

def main():
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        for rt in ("Observation","Patient"):
            cur.execute(SQL_BY_TYPE, (rt,))
            rows = cur.fetchall()
            extras = [r for r in rows if r[1] > 1]
            print(f"[{rt}] total distinct ids={len(rows)}; duplicates={len(extras)}")
            if extras:
                print("  top dupes:")
                for id_, n, first_seen, last_seen in extras[:10]:
                    print(f"   - {id_} x{n} (first={first_seen}, last={last_seen})")

        # Any exact dup rows overall?
        cur.execute("SELECT * FROM fhir_raw.v_resource_dupes LIMIT 50;")
        dupes = cur.fetchall()
        if dupes:
            print("\n[v_resource_dupes] (showing up to 50)")
            for rt, rid, n, first_seen, last_seen in dupes:
                print(f"  {rt} {rid} x{n} (first={first_seen}, last={last_seen})")
        else:
            print("\nNo JSON-level (type,id) duplicates detected.")
if __name__ == '__main__':
    main()
