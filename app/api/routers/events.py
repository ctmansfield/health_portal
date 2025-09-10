from fastapi import APIRouter, Query
from typing import Optional
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["events"])


@router.get("/events/recent")
def events_recent(
    limit: int = Query(100, ge=1, le=2000),
    since: Optional[str] = None,  # ISO-8601 timestamp
    code: Optional[str] = None,  # e.g., '8867-4'
):
    dsn = dsn_from_env()
    where = ["1=1"]
    params = []
    if since:
        where.append("effective_time >= %s")
        params.append(since)
    if code:
        where.append("code = %s")
        params.append(code)

    sql = f"""
        SELECT person_id, source, kind, code_system, code, value_num, unit, effective_time, meta
        FROM analytics.data_events
        WHERE {' AND '.join(where)}
        ORDER BY effective_time DESC
        LIMIT %s
    """
    params.append(limit)

    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"rows": rows, "count": len(rows)}
