from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import app.hp_etl.db as db
from app.hp_etl.cache import get as cache_get, set as cache_set
import uuid

router = APIRouter()


@router.get("/reports/{id}")
def get_report(id: str):
    """Return the canonical report payload JSON stored in analytics.report.payload by report.id (UUID).

    - 200: returns JSON payload verbatim
    - 400: invalid id format
    - 404: not found
    """
    # validate uuid
    try:
        uid = uuid.UUID(id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid id format")

    sql = "SELECT payload FROM analytics.report WHERE id = %s"
    with db.pg() as conn:
        cur = conn.cursor()
        cur.execute(sql, (str(uid),))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        payload = row[0]

    # Return payload verbatim with PHI-safe headers
    return JSONResponse(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


# New endpoint: critical-series
@router.get("/labs/{person_id}/critical-series")
def critical_series(
    person_id: str,
    metrics: str | None = None,
    since: str | None = None,
    until: str | None = None,
    agg: str | None = "daily",
):
    """Return time-series for critical lab/vital metrics.

    Query params:
      - metrics: comma separated list of metrics (e.g., hr,spo2)
      - since, until: optional ISO date strings (YYYY-MM-DD)

    Behavior:
      - If analytics.person does not contain person_id -> 404
      - If metrics is missing or invalid -> 400
      - Supported fallback metrics (when lab tables absent): hr, spo2
      - Unknown metric -> 501
      - Returns JSON array of { metric, unit, series: [{t, v}] }
      - Response header Cache-Control: no-store
    """
    if not metrics:
        raise HTTPException(status_code=400, detail="metrics parameter required")

    # normalize requested metrics and support aliases
    raw_requested = [m.strip().lower() for m in metrics.split(",") if m.strip()]
    if not raw_requested:
        raise HTTPException(status_code=400, detail="no metrics requested")

    # metric alias map
    ALIASES = {
        "heart_rate": "hr",
        "hr": "hr",
        "spo2": "spo2",
        "oxygen_saturation": "spo2",
        "o2sat": "spo2",
    }

    requested = [ALIASES.get(m, m) for m in raw_requested]

    # supported fallback metrics mapping
    METRICS = {
        "hr": {"col": "hr_median", "unit": "bpm", "label": "hr"},
        "spo2": {"col": "spo2_min", "unit": "%", "label": "spo2"},
    }

    # lab metrics mapping (requires analytics.lab_results or similar table to be present)
    LAB_METRICS = {
        "glucose": {"code": "GLU", "unit": "mg/dL"},
        "hemoglobin": {"code": "HGB", "unit": "g/dL"},
    }

    unknown = [m for m in requested if m not in METRICS and m not in LAB_METRICS]
    if unknown:
        # Unknown metrics are not supported
        raise HTTPException(
            status_code=501, detail=f"metrics not implemented: {', '.join(unknown)}"
        )

    # aggregation support
    if agg not in (None, "daily", "hourly"):
        # currently only daily and hourly (from data_events) are supported
        raise HTTPException(
            status_code=501, detail=f"aggregation not implemented: {agg}"
        )

    # robust date/datetime parsing (accept ISO date or datetime with tz)
    from datetime import date, datetime, timezone

    def _parse_to_date(s: str) -> date:
        # try date first
        try:
            return date.fromisoformat(s)
        except Exception:
            pass
        # try datetime
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            raise HTTPException(
                status_code=400, detail="invalid date format; use ISO date or datetime"
            )
        # assume naive datetimes are UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.date()

    since_date = None
    until_date = None
    try:
        if since:
            since_date = _parse_to_date(since)
        if until:
            until_date = _parse_to_date(until)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400, detail="invalid date format; use ISO date or datetime"
        )

    # Read ETL state to derive cache key / ttl
    etl_ver = None
    ttl_from_etl = None
    try:
        with db.pg() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT value FROM analytics.etl_state WHERE key = %s",
                    ("mv_daily_vitals_version",),
                )
                r = cur.fetchone()
                etl_ver = r[0] if r else None
            except Exception:
                etl_ver = None
            try:
                cur.execute(
                    "SELECT value FROM analytics.etl_state WHERE key = %s",
                    ("critical_series_ttl",),
                )
                r2 = cur.fetchone()
                ttl_from_etl = int(r2[0]) if r2 and r2[0] else None
            except Exception:
                ttl_from_etl = None
    except Exception:
        etl_ver = None
        ttl_from_etl = None

    cache_key = f"critical_series:{person_id}:{','.join(requested)}:{since or ''}:{until or ''}:{agg}:ver={etl_ver}"
    cached = cache_get(cache_key)
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "no-store"})

    # Check person existence (analytics.person) and fetch data
    with db.pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT tz FROM analytics.person WHERE person_id = %s LIMIT 1",
                (person_id,),
            )
            prow = cur.fetchone()
        except Exception:
            prow = None
        if not prow:
            raise HTTPException(status_code=404, detail="person not found")
        person_tz = prow[0] if prow and prow[0] else None

        # Hourly aggregation path (resample from analytics.data_events)
        hourly_results = {}
        if agg == "hourly":
            # parse since/until as datetimes (UTC)
            def _parse_to_dt_utc(s: str):
                try:
                    dts = datetime.fromisoformat(s)
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail="invalid datetime format; use ISO datetime",
                    )
                if dts.tzinfo is None:
                    dts = dts.replace(tzinfo=timezone.utc)
                return dts.astimezone(timezone.utc)

            since_dt = None
            until_dt = None
            try:
                if since:
                    since_dt = _parse_to_dt_utc(since)
                if until:
                    until_dt = _parse_to_dt_utc(until)
            except HTTPException:
                raise

            # mapping metrics to data_events code/system
            EVENT_CODES = {
                "hr": ("8867-4",),
                "spo2": ("59408-5",),
            }

            for m in requested:
                # prefer data_events for vitals (hr/spo2)
                if m in EVENT_CODES:
                    code = EVENT_CODES[m][0]
                    q = "SELECT date_trunc('hour', effective_time) as bucket, AVG(value_num) as avg_v FROM analytics.data_events WHERE person_id = %s AND code = %s"
                    params = [person_id, code]
                    if since_dt:
                        q += " AND effective_time >= %s"
                        params.append(since_dt)
                    if until_dt:
                        q += " AND effective_time <= %s"
                        params.append(until_dt)
                    q += " GROUP BY bucket ORDER BY bucket"
                    try:
                        cur.execute(q, tuple(params))
                        hourly_rows = cur.fetchall()
                    except Exception:
                        hourly_rows = []
                    hourly_results[m] = hourly_rows
                elif m in LAB_METRICS:
                    # try lab results table if present
                    lab_code = LAB_METRICS[m]["code"]
                    q = "SELECT date_trunc('hour', result_time) as bucket, AVG(result_value) as avg_v FROM analytics.lab_results WHERE person_id = %s AND code = %s"
                    params = [person_id, lab_code]
                    if since_dt:
                        q += " AND result_time >= %s"
                        params.append(since_dt)
                    if until_dt:
                        q += " AND result_time <= %s"
                        params.append(until_dt)
                    q += " GROUP BY bucket ORDER BY bucket"
                    try:
                        cur.execute(q, tuple(params))
                        hourly_rows = cur.fetchall()
                    except Exception:
                        # lab table not present or query failed -> 501 for this metric
                        raise HTTPException(
                            status_code=501, detail=f"lab metric not available: {m}"
                        )
                    hourly_results[m] = hourly_rows
                else:
                    hourly_results[m] = []
            # done; we'll process hourly_results below
            rows = None
        else:
            # fetch vitals fallback from analytics.mv_daily_vitals
            q = "SELECT day, hr_median, spo2_min FROM analytics.mv_daily_vitals WHERE person_id = %s"
            params = [person_id]
            if since_date:
                q += " AND day >= %s::date"
                params.append(str(since_date))
            if until_date:
                q += " AND day <= %s::date"
                params.append(str(until_date))
            q += " ORDER BY day ASC"

            try:
                cur.execute(q, tuple(params))
                rows = cur.fetchall()
            except Exception:
                rows = []

            # also try to fetch lab daily aggregates for requested lab metrics
            lab_daily = {}
            for m in requested:
                if m in LAB_METRICS:
                    lab_code = LAB_METRICS[m]["code"]
                    ql = "SELECT date_trunc('day', result_time)::date as day, AVG(result_value) as avg_v FROM analytics.lab_results WHERE person_id = %s AND code = %s"
                    pl = [person_id, lab_code]
                    if since_date:
                        ql += " AND result_time::date >= %s::date"
                        pl.append(str(since_date))
                    if until_date:
                        ql += " AND result_time::date <= %s::date"
                        pl.append(str(until_date))
                    ql += " GROUP BY day ORDER BY day ASC"
                    try:
                        cur.execute(ql, tuple(pl))
                        lab_rows = cur.fetchall()
                    except Exception:
                        # lab table missing or query failed: mark unavailable
                        raise HTTPException(
                            status_code=501, detail=f"lab metric not available: {m}"
                        )
                    lab_daily[m] = lab_rows

    # transform rows into per-metric series
    from zoneinfo import ZoneInfo

    out = []

    if agg == "hourly":
        # person_tz may be None
        try:
            local_tz = ZoneInfo(person_tz) if person_tz else ZoneInfo("UTC")
        except Exception:
            local_tz = ZoneInfo("UTC")

        for m in requested:
            meta = METRICS[m]
            series = []
            rows_h = hourly_results.get(m, [])
            for r in rows_h:
                # r[0]=bucket (datetime), r[1]=avg_v
                bucket = r[0]
                avgv = r[1]
                if bucket is None:
                    continue
                # ensure tz-aware
                if bucket.tzinfo is None:
                    bucket = bucket.replace(tzinfo=timezone.utc)
                t_utc = (
                    bucket.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                try:
                    t_local = bucket.astimezone(local_tz).isoformat()
                except Exception:
                    t_local = None
                series.append(
                    {
                        "t_utc": t_utc,
                        "t_local": t_local,
                        "v": float(avgv) if avgv is not None else None,
                    }
                )
            out.append(
                {
                    "metric": m,
                    "unit": meta["unit"],
                    "tz": person_tz or "UTC",
                    "series": series,
                }
            )
    else:
        for m in requested:
            if m in METRICS:
                meta = METRICS[m]
                series = []
                for r in rows:
                    # r[0]=day, r[1]=hr_median, r[2]=spo2_min
                    dt_obj = None
                    if isinstance(r[0], str):
                        # try to parse
                        try:
                            dt_obj = datetime.fromisoformat(r[0])
                        except Exception:
                            dt_obj = None
                    else:
                        # assume date/datetime
                        try:
                            if hasattr(r[0], "isoformat") and not hasattr(
                                r[0], "tzinfo"
                            ):
                                # date object
                                dt_obj = datetime.combine(
                                    r[0], datetime.min.time(), tzinfo=timezone.utc
                                )
                            elif hasattr(r[0], "tzinfo"):
                                dt_obj = r[0].astimezone(timezone.utc)
                            else:
                                dt_obj = datetime.fromisoformat(str(r[0]))
                        except Exception:
                            dt_obj = None

                    if dt_obj is None:
                        ts = None
                    else:
                        # ensure UTC
                        if dt_obj.tzinfo is None:
                            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                        dt_utc = dt_obj.astimezone(timezone.utc)
                        ts = dt_utc.isoformat().replace("+00:00", "Z")

                    if m == "hr":
                        val = r[1]
                    elif m == "spo2":
                        val = r[2]
                    else:
                        val = None
                    series.append({"t": ts, "v": val})
                out.append(
                    {"metric": m, "unit": meta["unit"], "tz": "UTC", "series": series}
                )
            elif m in LAB_METRICS:
                meta = LAB_METRICS[m]
                series = []
                lab_rows = lab_daily.get(m, [])
                for r in lab_rows:
                    # r[0]=day (date), r[1]=avg_v
                    day = r[0]
                    avgv = r[1]
                    try:
                        dt_obj = datetime.combine(
                            day, datetime.min.time(), tzinfo=timezone.utc
                        )
                        t_utc = (
                            dt_obj.astimezone(timezone.utc)
                            .isoformat()
                            .replace("+00:00", "Z")
                        )
                    except Exception:
                        t_utc = None
                    series.append(
                        {"t": t_utc, "v": float(avgv) if avgv is not None else None}
                    )
                out.append(
                    {
                        "metric": m,
                        "unit": meta.get("unit"),
                        "tz": "UTC",
                        "series": series,
                    }
                )

    # store in process cache (ttl may be controlled via analytics.etl_state key "critical_series_ttl")
    ttl = ttl_from_etl if ttl_from_etl is not None else 30
    try:
        cache_set(cache_key, out, ttl=ttl)
    except Exception:
        pass

    return JSONResponse(content=out, headers={"Cache-Control": "no-store"})
