# app/api/routers/liver.py
from fastapi import APIRouter, Query
from typing import Optional, Any, Dict, List
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["liver"])


@router.get("/liver/latest")
def liver_latest() -> Dict[str, Any]:
    sql = """
      SELECT person_id, alt_uL, ast_uL, alp_uL, ggt_uL, bili_total_mgdl, bili_direct_mgdl, albumin_gdl, updated_at
      FROM analytics.v_liver_latest
      ORDER BY updated_at DESC NULLS LAST
    """
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return {"rows": [dict(zip(cols, r)) for r in cur.fetchall()]}


@router.get("/liver/daily")
def liver_daily(
    days: int = Query(90, ge=1, le=365), person_id: Optional[str] = None
) -> Dict[str, Any]:
    where = ["day >= current_date - %s::int"]
    params: List[Any] = [days]
    if person_id:
        where.append("person_id = %s")
        params.append(person_id)
    sql = f"""
      SELECT person_id, day, alt_p50, ast_p50, alp_p50, ggt_p50, bili_total_max, bili_direct_max, albumin_p50
      FROM analytics.mv_liver_daily
      WHERE {' AND '.join(where)}
      ORDER BY day DESC, person_id
    """
    dsn = dsn_from_env()
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return {"rows": [dict(zip(cols, r)) for r in cur.fetchall()]}
