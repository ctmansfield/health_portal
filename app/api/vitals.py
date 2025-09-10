from fastapi import APIRouter, Query
from hp_etl.db import pg, dsn_from_env
import os

router = APIRouter(prefix="/vitals", tags=["vitals"])

SQL = """
SELECT person_id, day, hr_median, spo2_min
FROM analytics.mv_daily_vitals
WHERE (%(since)s IS NULL OR day >= %(since)s::date)
ORDER BY day DESC
LIMIT %(limit)s
"""


@router.get("/daily")
def daily_vitals(since: str | None = None, limit: int = Query(30, le=365)):
    dsn = os.getenv("HP_DSN", dsn_from_env())
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(SQL, {"since": since, "limit": limit})
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
