from fastapi import APIRouter, Query
from hp_etl.db import pg, dsn_from_env
import os

router = APIRouter(prefix="/findings", tags=["findings"])

SQL = """
SELECT person_id, finding_time, metric, method, score, level, window, context
FROM analytics.ai_findings
WHERE (%(since)s IS NULL OR finding_time >= %(since)s)
ORDER BY finding_time DESC
LIMIT %(limit)s
"""


@router.get("")
def list_findings(since: str | None = None, limit: int = Query(50, le=500)):
    dsn = os.getenv("HP_DSN", dsn_from_env())
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(SQL, {"since": since, "limit": limit})
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
