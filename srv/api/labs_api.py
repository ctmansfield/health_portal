from fastapi import APIRouter, HTTPException
import os
import psycopg

router = APIRouter(prefix="/labs", tags=["labs"])
PG_DSN = (
    os.environ.get("PG_DSN")
    or "host=localhost port=5432 dbname=health_portal user=postgres"
)


@router.get("/{person_id}/critical-series")
def critical_series(person_id: str, metrics: str = "", agg: str = "daily"):
    allow = {m.strip().lower() for m in (metrics or "").split(",") if m.strip()}
    try:
        with psycopg.connect(PG_DSN) as conn:
            cur = conn.execute(
                """
              SELECT metric_name AS metric, t_utc, value_num AS v
              FROM analytics.mv_critical_labs
              WHERE person_id=%s
              ORDER BY t_utc ASC""",
                (person_id,),
            )
            out = {}
            for r in cur.fetchall():
                m = (r[0] or "").lower().replace(" ", "")
                if allow and m not in allow:
                    continue
                out.setdefault(m, []).append({"t_utc": r[1].isoformat(), "v": r[2]})
        return [{"metric": k, "series": v} for k, v in out.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
