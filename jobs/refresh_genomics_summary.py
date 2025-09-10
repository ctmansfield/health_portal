#!/usr/bin/env python3
"""Refresh only the genomics summary materialized view.
Safe to run from cron and uses HP_DSN or --dsn.
"""
import argparse
from hp_etl.db import pg

VIEW = "analytics.mv_genomics_summary"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()

    with pg(args.dsn) as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {VIEW}")
            print(VIEW, "refreshed concurrently")
        except Exception:
            cur.execute(f"REFRESH MATERIALIZED VIEW {VIEW}")
            print(VIEW, "refreshed non-concurrently")


if __name__ == "__main__":
    main()
