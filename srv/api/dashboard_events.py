from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from app.hp_etl.db import pg
from srv.api.auth import require_api_key
from app.hp_etl.simple_cache import get as cache_get, set as cache_set
import json

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")


@router.get("/dashboard/events")
async def dashboard_events(request: Request, person_id: str = "me"):
    # Render page; JS will fetch data
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "events": [],
            "person_id": person_id,
            "metric": None,
            "day": None,
        },
    )


@router.get("/dashboard/events.json")
async def dashboard_events_json(
    person_id: str = Query("me"),
    metric: str | None = Query(None),
    day: str | None = Query(None),
    limit: int = Query(100),
    auth=Depends(require_api_key),
):
    """Return JSON list of events with optional caching (ttl=30s)."""
    cache_key = f"events:{person_id}:{metric}:{day}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return JSONResponse(cached)

    where = ["person_id = %s"]
    params = [person_id]
    if metric:
        if metric == "hr":
            where.append("code = %s")
            params.append("8867-4")
        elif metric == "spo2":
            where.append("code = %s")
            params.append("59408-5")
        else:
            where.append("code = %s")
            params.append(metric)
    if day:
        where.append("(effective_time::date) = %s::date")
        params.append(day)
    q = f"SELECT person_id, source, kind, code_system, code, display, effective_time, value_num, unit, meta FROM analytics.data_events WHERE {' AND '.join(where)} ORDER BY effective_time DESC LIMIT %s"
    params.append(limit)
    with pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(q, tuple(params))
            rows = cur.fetchall()
        except Exception:
            rows = []
    events = [
        dict(
            person_id=r[0],
            source=r[1],
            kind=r[2],
            code_system=r[3],
            code=r[4],
            display=r[5],
            effective_time=r[6].isoformat() if r[6] else None,
            value_num=r[7],
            unit=r[8],
            meta=r[9],
        )
        for r in rows
    ]
    cache_set(cache_key, events, ttl=30)
    return JSONResponse(events)
