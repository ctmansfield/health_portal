#!/usr/bin/env python3
"""
Refresh materialized views used by the dashboard.
- Attempts REFRESH MATERIALIZED VIEW CONCURRENTLY where possible, falls back to non-concurrent.
- Safe to run from cron with flock locking.
"""

import argparse
import sys
from hp_etl.db import pg

VIEWS = [
    "analytics.mv_daily_vitals",
    "analytics.mv_vitals_daily_wide",
    "analytics.mv_events_daily",
    "analytics.mv_hr_hourly",
    "analytics.mv_spo2_daily_pct",
    "analytics.mv_hr_daily_zscore",
]


def refresh_view(cur, view):
    try:
        cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
        return True, "concurrent"
    except Exception:
        # fallback
        cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
        return True, "non-concurrent"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()

    results = []
    with pg(args.dsn) as conn:
        cur = conn.cursor()
        for v in VIEWS:
            try:
                ok, mode = refresh_view(cur, v)
                results.append((v, True, mode))
            except Exception as e:
                results.append((v, False, str(e)))
    for r in results:
        print(r)
    # exit with non-zero if any failed
    if any(not ok for _, ok, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
