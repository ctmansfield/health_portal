from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
import app.hp_etl.db as db
from app.hp_etl.cache import get as cache_get, set as cache_set
from .auth import require_api_key
import datetime as dt
from urllib.parse import parse_qs
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")
# allow loading component partials from app/templates as well (component lives in app/templates/components)
try:
    templates.env.loader.searchpath.append("app/templates")
except Exception:
    pass


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
    since = (
        (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()
    )
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


# UI routes for previewing the report summary card component
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pathlib import Path


def _no_store_headers(resp: Response) -> Response:
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Frame-Options"] = "DENY"
    return resp


@router.get("/ui/components/report-summary-card", response_class=HTMLResponse)
async def ui_component_report_summary_card(request: Request, id: str | None = None):
    """Return the component partial standalone. Optional query param ?id=<uuid>"""
    tpl = templates.get_template("components/report_summary_card.html")
    html = tpl.render(request=request, report_id=(id or ""))
    resp = HTMLResponse(content=html, status_code=200)
    return _no_store_headers(resp)


@router.get("/ui/reports/{id}/summary-card", response_class=HTMLResponse)
async def ui_report_summary_card(request: Request, id: str):
    """Return a full page that includes the component for a given report id."""
    tpl = templates.get_template("components/report_summary_card.html")
    html = tpl.render(request=request, report_id=id)
    resp = HTMLResponse(content=html, status_code=200)
    return _no_store_headers(resp)


@router.get("/ui/demo/report-summary", response_class=HTMLResponse)
async def ui_demo_report_summary(request: Request):
    """Small demo wrapper page that embeds the report summary card component into a simple dashboard-like container."""
    partial_tpl = templates.get_template("components/report_summary_card.html")
    partial_html = partial_tpl.render(
        request=request, report_id="00000000-0000-0000-0000-000000000000"
    )
    return _no_store_headers(
        templates.TemplateResponse(
            "demo_report_summary.html", {"request": request, "partial": partial_html}
        )
    )


@router.get("/ui", response_class=HTMLResponse)
async def ui_index(request: Request):
    """Small index listing useful UI pages for quick review."""
    sample_id = "00000000-0000-0000-0000-000000000000"
    return templates.TemplateResponse(
        "ui_index.html", {"request": request, "sample_id": sample_id}
    )


@router.get("/ui/people/{id}/labs/critical", response_class=HTMLResponse)
async def ui_people_labs_critical(request: Request, id: str):
    """Render the labs critical graphs page for a person (client-side will fetch series via APP-9).
    The page can request preview data from /ui/preview/labs/{person_id} when preview mode is active.
    """
    tpl = templates.get_template("components/labs_critical_page.html")
    html = tpl.render(request=request, person_id=id)
    resp = HTMLResponse(content=html, status_code=200)
    return _no_store_headers(resp)


@router.get("/ui/preview/labs/{person_id}")
async def ui_preview_labs(request: Request, person_id: str):
    """Return a small sample preview dataset for the labs page (used by designers).
    Response is no-store and safe for embedding in the UI.
    """
    sample = [
        {
            "metric": "hr",
            "unit": "bpm",
            "tz": "UTC",
            "series": [
                {
                    "t_utc": "2025-09-01T00:00:00Z",
                    "t_local": "2025-08-31T17:00:00-07:00",
                    "v": 60,
                },
                {
                    "t_utc": "2025-09-02T00:00:00Z",
                    "t_local": "2025-09-01T17:00:00-07:00",
                    "v": 62,
                },
            ],
        },
        {
            "metric": "spo2",
            "unit": "%",
            "tz": "UTC",
            "series": [
                {
                    "t_utc": "2025-09-01T00:00:00Z",
                    "t_local": "2025-08-31T17:00:00-07:00",
                    "v": 98,
                },
                {
                    "t_utc": "2025-09-02T00:00:00Z",
                    "t_local": "2025-09-01T17:00:00-07:00",
                    "v": 97,
                },
            ],
        },
    ]
    return _no_store_headers(JSONResponse(content=sample))
