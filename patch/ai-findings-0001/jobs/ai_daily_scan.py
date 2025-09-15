#!/usr/bin/env python3
import argparse
import json
import datetime as dt
from typing import List, Tuple
from hp_etl.db import pg, dsn_from_env
from hp_etl.state import get_state, set_state
from hp_etl.anom import rolling_zscore, level_from_score

METRICS = {
    "hr": ("8867-4", "median"),
    "spo2": ("59408-5", "min"),
}


def fetch_days(code: str, agg: str, dsn: str) -> List[Tuple[str, float]]:
    sql = f"""
      with src as (
        select effective_time::date as d, value_num
        from analytics.data_events
        where code_system='LOINC' and code=%s and value_num is not null
          and effective_time >= now() - interval '60 days'
      )
      select d::text, {"percentile_disc(0.5) within group (order by value_num)" if agg == "median" else "min(value_num)"}
      from src group by 1 order by 1;
    """
    out = []
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, (code,))
        for d, v in cur.fetchall():
            if v is not None:
                iso = dt.date.fromisoformat(d).strftime("%Y-%m-%dT00:00:00Z")
                out.append((iso, float(v)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=dsn_from_env())
    ap.add_argument("--person-id", default="me")
    args = ap.parse_args()

    last = get_state("ai_last_day", args.dsn)
    newest = last
    inserts = 0

    for metric, (code, agg) in METRICS.items():
        days = fetch_days(code, agg, args.dsn)
        zs = rolling_zscore(days, window=21)
        for (ts, val), (_, z) in zip(days, zs):
            if z is None:
                continue
            if last and ts <= last:
                continue
            lvl = level_from_score(z)
            window = {"n": min(21, len(days)), "metric": metric, "agg": agg}
            ctx = {"value": val, "code": code}
            with pg(args.dsn) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics.ai_findings
                      (person_id, finding_time, metric, method, score, level, window, context)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                    ON CONFLICT (person_id, finding_time, metric) DO NOTHING
                """,
                    (
                        args.person_id,
                        ts,
                        metric,
                        "zscore",
                        float(z),
                        lvl,
                        json.dumps(window),
                        json.dumps(ctx),
                    ),
                )
                inserts += cur.rowcount
            if newest is None or ts > newest:
                newest = ts

    if newest:
        set_state("ai_last_day", newest, args.dsn)
        print(f"ai_last_day -> {newest} | inserts: {inserts}")


if __name__ == "__main__":
    main()
