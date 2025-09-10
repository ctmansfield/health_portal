from fastapi import APIRouter
from hp_etl.db import pg, dsn_from_env

router = APIRouter(tags=["summary"])


@router.get("/health/summary")
def health_summary():
    dsn = dsn_from_env()
    out = {}

    with pg(dsn) as conn, conn.cursor() as cur:
        # FHIR counts
        cur.execute(
            "SELECT resource_type, COUNT(*) FROM fhir_raw.resources GROUP BY 1 ORDER BY 1;"
        )
        out["fhir_counts"] = [
            {"resource_type": rt, "n": n} for (rt, n) in cur.fetchall()
        ]

        # events min/max/count
        cur.execute(
            "SELECT MIN(effective_time), MAX(effective_time), COUNT(*) FROM analytics.data_events;"
        )
        mn, mx, c = cur.fetchone()
        out["events"] = {"min": mn, "max": mx, "n": c}

        # latest vitals quick card
        try:
            cur.execute(
                "SELECT person_id, hr_latest, spo2_latest, updated_at FROM analytics.v_vitals_latest ORDER BY person_id;"
            )
            cols = [d.name for d in cur.description]
            out["vitals_latest"] = [dict(zip(cols, r)) for r in cur.fetchall()]
        except Exception:
            out["vitals_latest"] = []

    return out
