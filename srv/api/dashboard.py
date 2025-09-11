from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import app.hp_etl.db as db
from app.hp_etl.simple_cache import get as cache_get, set as cache_set
from .auth import require_api_key
import datetime as dt
from urllib.parse import parse_qs
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


@router.post("/login")
async def login_post(request: Request):
    # Try parsing form first (works if python-multipart is installed).
    # Fall back to JSON or urlencoded body parsing so tests do not require python-multipart.
    api_key = None
    try:
        form = await request.form()
        api_key = form.get("api_key")
    except Exception:
        # fallback to JSON
        try:
            body_json = await request.json()
            if isinstance(body_json, dict):
                api_key = body_json.get("api_key")
        except Exception:
            # fallback to parse urlencoded body (e.g., tests sending data=...)
            try:
                body = (await request.body()).decode()
                parsed = parse_qs(body)
                api_key = parsed.get("api_key", [None])[0]
            except Exception:
                api_key = None

    hp_key = os.environ.get("HP_API_KEY")
    if not hp_key:
        resp = RedirectResponse(url="/dashboard", status_code=303)
        return resp
    if api_key == hp_key:
        resp = RedirectResponse(url="/dashboard", status_code=303)
        resp.set_cookie("hp_api_key", api_key, httponly=True, path="/", samesite="Lax")
        return resp
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid key"}
    )


@router.get("/logout")
def logout(request: Request):
    resp = templates.TemplateResponse("logged_out.html", {"request": request})
    resp.delete_cookie("hp_api_key", path="/")
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    person_id: str = "me",
    days: int = 14,
    auth=Depends(require_api_key),
):
    since = (dt.datetime.utcnow() - dt.timedelta(days=days)).date().isoformat()
    # cache key
    cache_key = f"dashboard:{person_id}:{days}"
    cached = cache_get(cache_key)
    if cached is not None:
        return templates.TemplateResponse(
            "dashboard.html", {**cached, "request": request}
        )

    with db.pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT day, hr_median, spo2_min FROM analytics.mv_daily_vitals WHERE person_id = %s AND day >= %s::date ORDER BY day ASC",
                (person_id, since),
            )
            vitals = cur.fetchall()
        except Exception:
            vitals = []
        try:
            cur.execute(
                "SELECT metric, level, score, context, finding_time FROM analytics.ai_findings WHERE person_id = %s AND finding_time >= %s ORDER BY finding_time DESC LIMIT 50",
                (person_id, since),
            )
            findings = cur.fetchall()
        except Exception:
            findings = []

    labels = [r[0].isoformat() for r in vitals]
    hr_values = [r[1] for r in vitals]
    spo2_values = [r[2] for r in vitals]
    findings_list = [
        dict(metric=r[0], level=r[1], score=r[2], context=r[3], finding_time=r[4])
        for r in findings
    ]

    ctx = {
        "person_id": person_id,
        "days": days,
        "labels": labels,
        "hr_values": hr_values,
        "spo2_values": spo2_values,
        "findings": findings_list,
    }
    cache_set(cache_key, ctx, ttl=30)
    return templates.TemplateResponse("dashboard.html", {**ctx, "request": request})
