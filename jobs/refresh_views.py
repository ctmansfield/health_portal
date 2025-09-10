#!/usr/bin/env python3
from hp_etl.db import pg, dsn_from_env

SQLS = [
    "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_events_daily",
    "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_vitals_daily_wide",
    "REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_daily_vitals",
    "REFRESH MATERIALIZED VIEW analytics.mv_weight_daily",
]


def main():
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        for stmt in SQLS:
            try:
                cur.execute(stmt)
            except Exception:
                # fallback non-concurrent if needed
                cur.execute(stmt.replace(" CONCURRENTLY", ""))
    print("Views refreshed.")


if __name__ == "__main__":
    main()
