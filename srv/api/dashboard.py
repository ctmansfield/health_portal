from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import app.hp_etl.db as db
from app.hp_etl.simple_cache import get as cache_get, set as cache_set
from .auth import require_api_key
import datetime as dt

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request, "login.html", {"request": request, "error": error}
    )


@router.post("/login")
async def login_post(request: Request):
    # support both form-encoded and JSON bodies (tests may post JSON without python-multipart)
    try:
        form = await request.form()
        api_key = form.get("api_key")
    except Exception:
        try:
            j = await request.json()
            api_key = j.get("api_key") if isinstance(j, dict) else None
        except Exception:
            api_key = None
    import os

    hp_key = os.environ.get("HP_API_KEY")
    from fastapi.responses import JSONResponse

    if not hp_key:
        # no API key required in this deployment; behave as successful
        return JSONResponse({"ok": True})
    if api_key == hp_key:
        resp = JSONResponse({"ok": True})
        resp.set_cookie("hp_api_key", api_key, httponly=True, path="/", samesite="Lax")
        return resp
    return templates.TemplateResponse(
        request, "login.html", {"request": request, "error": "Invalid key"}
    )


@router.get("/logout")
def logout(request: Request):
    resp = templates.TemplateResponse(request, "logged_out.html", {"request": request})
    resp.delete_cookie("hp_api_key", path="/")
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    person_id: str = "me",
    days: int = 14,
    auth=Depends(require_api_key),
):
    since = (
        (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()
    )
    # cache key
    cache_key = f"dashboard:{person_id}:{days}"
    cached = cache_get(cache_key)
    if cached is not None:
        return templates.TemplateResponse(
            request, "dashboard.html", {**cached, "request": request}
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
    return templates.TemplateResponse(
        request, "dashboard.html", {**ctx, "request": request}
    )
