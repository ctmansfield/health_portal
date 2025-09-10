from fastapi import APIRouter, Query
from typing import Optional, Dict, Any, List
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["anomalies"])


@router.get("/anomalies/vitals")
def vitals_anomalies(
    since: Optional[str] = Query(
        None, description="ISO timestamptz; filter effective_time >= since"
    ),
    code: Optional[str] = Query(
        None, description="LOINC code e.g., 8867-4, 59408-5, 29463-7"
    ),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    days: Optional[int] = Query(None, ge=1, le=365),
) -> Dict[str, Any]:
    dsn = dsn_from_env()
    where: List[str] = ["1=1"]
    params: List[Any] = []
    # allow days as a convenience when since is not provided
    if not since and days:
        where.append("effective_time >= now() - make_interval(days => %s)")
        params.append(days)
    if since:
        where.append("effective_time >= %s")
        params.append(since)
    if code:
        where.append("code = %s")
        params.append(code)

    sql = f"""
      SELECT person_id, effective_time, code_system, code, value_num, reason
      FROM analytics.v_vitals_anomalies
      WHERE {' AND '.join(where)}
      ORDER BY effective_time DESC
      LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"rows": rows, "limit": limit, "offset": offset}


# compatibility alias for tests/UI hitting /vitals/anomalies
router.add_api_route("/vitals/anomalies", vitals_anomalies, methods=["GET"])
