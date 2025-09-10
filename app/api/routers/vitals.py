from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["vitals"])


@router.get("/vitals/latest")
def vitals_latest() -> Dict[str, Any]:
    dsn = dsn_from_env()
    sql = "SELECT person_id, hr_latest, spo2_latest, updated_at FROM analytics.v_vitals_latest ORDER BY person_id"
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"rows": rows}


@router.get("/vitals/daily")
def vitals_daily(
    days: int = Query(30, ge=1, le=365), person_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns daily median HR and min SpO2 for the last N days.
    Reads analytics.mv_vitals_daily_wide (materialized).
    """
    dsn = dsn_from_env()
    where = ["day >= current_date - %s::int"]
    params: List[Any] = [days]
    if person_id:
        where.append("person_id = %s")
        params.append(person_id)
    sql = f"""
      SELECT person_id, day::date, hr_median, spo2_min
      FROM analytics.mv_vitals_daily_wide
      WHERE {' AND '.join(where)}
      ORDER BY day DESC, person_id
    """
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"rows": rows}


@router.get("/bp/latest")
def bp_latest() -> Dict[str, Any]:
    dsn = dsn_from_env()
    sql = """
      SELECT person_id, systolic_mmhg, diastolic_mmhg, updated_at
      FROM analytics.v_bp_latest
      ORDER BY person_id
    """
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"rows": rows}
