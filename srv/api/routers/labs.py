from fastapi import APIRouter, Path, Query, HTTPException
from typing import List, Dict, Any
import os
import psycopg
from psycopg.rows import dict_row
from app.hp_etl import db as hp_db

router = APIRouter(prefix="/labs", tags=["labs"])

@router.get("/metrics-catalog", response_model=List[Dict[str, Any]])
def metrics_catalog(
    code_system: str = Query("LOINC", description="Filter by code system (default LOINC)"),
    include_disabled: bool = Query(False, description="Include disabled entries")
) -> List[Dict[str, Any]]:
    try:
        with hp_db.pg(_conninfo()) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                sql = (
                    "SELECT code_system, code, label, label_key_norm, group_name, sensitive, unit, enabled "
                    "FROM analytics.labs_metric_catalog WHERE code_system ILIKE %s"
                )
                params = [code_system]
                if not include_disabled:
                    sql += " AND enabled IS TRUE"
                sql += " ORDER BY group_name, label"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"metrics-catalog query failed: {e}")


def _conninfo() -> str:
    # Prefer the shared HP_DSN used by the app to ensure consistent DB and schema
    try:
        return hp_db.dsn_from_env()
    except Exception:
        url = os.getenv("DATABASE_URL")
        if url:
            return url
        host = os.getenv("PGHOST", "localhost")
        port = os.getenv("PGPORT", "5432")
        dbname = os.getenv("PGDATABASE", "postgres")
        user = os.getenv("PGUSER", "postgres")
        pwd = os.getenv("PGPASSWORD", "")
        return f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"

@router.get("/{person_id}/labs-metadata", response_model=List[Dict[str, Any]])
def labs_metadata(
    person_id: str = Path(..., description="Patient/person identifier"),
    include_sensitive: bool = Query(True, description="Include items flagged Sensitive")
) -> List[Dict[str, Any]]:
    try:
        with hp_db.pg(_conninfo()) as conn:
            if include_sensitive:
                sql = """
                    WITH base AS (
                      SELECT
                        g.label_key_norm AS metric,
                        g.label,
                        COALESCE(g.group_name, 'Other') AS group_name,
                        g.sensitive,
                        COALESCE(cnt.series_count, 0) AS series_count
                      FROM analytics.v_labs_all_grouped g
                      LEFT JOIN (
                        SELECT label, COUNT(*) AS series_count
                        FROM analytics.v_labs_all
                        WHERE person_id = %s AND value_num IS NOT NULL
                        GROUP BY label
                      ) cnt ON cnt.label = g.label
                      WHERE g.person_id = %s
                    ), ranked AS (
                      SELECT *, ROW_NUMBER() OVER (PARTITION BY metric ORDER BY series_count DESC, label) AS rn
                      FROM base
                    )
                    SELECT metric, label, group_name, sensitive, series_count
                    FROM ranked
                    WHERE rn = 1
                    ORDER BY group_name, label
                """
                params = (person_id, person_id)
            else:
                sql = """
                    WITH base AS (
                      SELECT
                        g.label_key_norm AS metric,
                        g.label,
                        COALESCE(g.group_name, 'Other') AS group_name,
                        g.sensitive,
                        COALESCE(cnt.series_count, 0) AS series_count
                      FROM analytics.v_labs_all_grouped g
                      LEFT JOIN (
                        SELECT label, COUNT(*) AS series_count
                        FROM analytics.v_labs_all
                        WHERE person_id = %s AND value_num IS NOT NULL
                        GROUP BY label
                      ) cnt ON cnt.label = g.label
                      WHERE g.person_id = %s AND NOT g.sensitive
                    ), ranked AS (
                      SELECT *, ROW_NUMBER() OVER (PARTITION BY metric ORDER BY series_count DESC, label) AS rn
                      FROM base
                    )
                    SELECT metric, label, group_name, sensitive, series_count
                    FROM ranked
                    WHERE rn = 1
                    ORDER BY group_name, label
                """
                params = (person_id, person_id)
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"labs-metadata query failed: {e}")

@router.get("/{person_id}/all-series", response_model=List[Dict[str, Any]])
def all_series(
    person_id: str = Path(..., description="Patient/person identifier"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD) UTC filter"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD) UTC filter")
) -> List[Dict[str, Any]]:
    try:
        with hp_db.pg(_conninfo()) as conn:
            sql = (
                "SELECT v.label, v.day AS t_utc, v.value_num "
                "FROM analytics.v_labs_all v "
                "WHERE v.person_id = %s AND v.value_num IS NOT NULL"
            )
            params: list[Any] = [person_id]
            if start_date:
                sql += " AND v.day >= %s::date"
                params.append(start_date)
            if end_date:
                sql += " AND v.day <= %s::date"
                params.append(end_date)
            sql += " ORDER BY v.label, v.day"
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

                # Build label -> metric key map (normalized) for this person
                cur.execute(
                    """
                    SELECT DISTINCT label, label_key_norm
                    FROM analytics.v_labs_all_grouped
                    WHERE person_id = %s
                    """,
                    (person_id,)
                )
                map_rows = cur.fetchall()

        label_to_metric = {r["label"]: (r["label_key_norm"] or (r["label"] or "").strip().lower()) for r in map_rows}

        series_by_metric: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            label = r["label"]
            metric = label_to_metric.get(label, (label or "").strip().lower())
            t_utc = r["t_utc"]
            v = r["value_num"]
            point = {"t_utc": t_utc.isoformat() if hasattr(t_utc, "isoformat") else str(t_utc), "v": v}
            series_by_metric.setdefault(metric, []).append(point)

        return [{"metric": m, "series": pts} for m, pts in series_by_metric.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"all-series query failed: {e}")

