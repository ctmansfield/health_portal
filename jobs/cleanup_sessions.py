#!/usr/bin/env python3
"""
Cleanup expired sessions from analytics.sessions.
Intended to run daily from cron. Uses HP_DSN env or --dsn.
"""
import argparse
import os
from hp_etl.db import pg

SQL_DELETE = """
DELETE FROM analytics.sessions
WHERE expires_at IS NOT NULL AND expires_at < now()
RETURNING session_id
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()

    with pg(args.dsn) as conn:
        cur = conn.cursor()
        cur.execute(SQL_DELETE)
        rows = cur.fetchall()
        n = len(rows) if rows else 0
    print(f"cleanup_sessions: removed {n} expired sessions")


if __name__ == "__main__":
    main()
