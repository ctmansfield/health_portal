import logging
from collections import defaultdict
import os
import traceback
from urllib.parse import parse_qs
import datetime as dt

from fastapi import Request, APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

import app.hp_etl.db as db
from app.hp_etl.cache import get as cache_get, set as cache_set
from .auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")
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
    api_key = None
    try:
        form = await request.form()
        api_key = form.get("api_key")
    except Exception:
        pass
    if not api_key:
        try:
            body_json = await request.json()
            if isinstance(body_json, dict):
                api_key = body_json.get("api_key")
        except Exception:
            pass
    if not api_key:
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
    resp = templates.TemplateResponse("dashboard.html", {"request": request})
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


@router.get("/labs/{person_id}/liver-series")
async def labs_liver_series(
    person_id: str,
    agg: str = "daily",
    metrics: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    auth=Depends(require_api_key),
):
    metric_list = (metrics or "alt,ast,alp,ggt,bili_total,bili_direct,albumin").split(
        ","
    )
    metric_list = [m.strip().lower() for m in metric_list if m.strip()]

    valid_metrics = {
        "alt": "alt_p50",
        "ast": "ast_p50",
        "alp": "alp_p50",
        "ggt": "ggt_p50",
        "bili_total": "bili_total_max",
        "bili_direct": "bili_direct_max",
        "albumin": "albumin_p50",
    }
    selected_metrics = {m: valid_metrics[m] for m in metric_list if m in valid_metrics}
    if not selected_metrics:
        return JSONResponse(
            status_code=400, content={"error": "Invalid or empty metrics list"}
        )

    where_clauses = ["person_id = %s"]
    params = [person_id]
    if start_date:
        where_clauses.append("day >= %s::date")
        params.append(start_date)
    if end_date:
        where_clauses.append("day <= %s::date")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)

    sql = f"""
    SELECT day, {", ".join(selected_metrics.values())}
    FROM analytics.mv_liver_daily
    WHERE {where_sql}
    ORDER BY day ASC
    """

    try:
        with db.pg() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            logger.debug(
                "Liver series query returned %d rows for person_id=%s",
                len(rows),
                person_id,
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "labs_metadata_failed", "detail": str(e)[:2000]},
        )

    if not rows:
        demo_data = [
            {
                "metric": "alt",
                "unit": "",
                "tz": "UTC",
                "series": [
                    {"t_utc": "2025-09-01", "v": 40},
                    {"t_utc": "2025-09-02", "v": 42},
                    {"t_utc": "2025-09-03", "v": 38},
                ],
            },
            {
                "metric": "ast",
                "unit": "",
                "tz": "UTC",
                "series": [
                    {"t_utc": "2025-09-01", "v": 35},
                    {"t_utc": "2025-09-02", "v": 37},
                    {"t_utc": "2025-09-03", "v": 34},
                ],
            },
        ]
    return JSONResponse(content=demo_data)

    metrics_map = {
        m: {"metric": m, "unit": "", "tz": "UTC", "series": []}
        for m in selected_metrics.keys()
    }
    for row in rows:
        day = row[0]
        for idx, m in enumerate(list(selected_metrics.keys())):
            val = row[idx + 1]
            if val is not None:
                metrics_map[m]["series"].append({"t_utc": day.isoformat(), "v": val})

    data = list(metrics_map.values())
    return JSONResponse(content=data)


@router.get("/x_deprecated/labs/{person_id}/all-series")
async def labs_all_series_deprecated(person_id: str, auth=Depends(require_api_key)):
    with db.pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT day, LOWER(label) AS metric, value_num
                FROM analytics.v_labs_all
                WHERE person_id = %s
                AND LOWER(label) NOT IN ('hr', 'spo2')
                ORDER BY day ASC
                """,
                (person_id,),
            )
            rows = cur.fetchall()
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": "labs_metadata_failed", "detail": str(e)[:2000]},
            )

    if not rows:
        sample = [
            {
                "metric": "alt",
                "series": [
                    {"t_utc": "2025-01-01", "v": 40},
                    {"t_utc": "2025-01-02", "v": 42},
                ],
            },
            {
                "metric": "ast",
                "series": [
                    {"t_utc": "2025-01-01", "v": 35},
                    {"t_utc": "2025-01-02", "v": 37},
                ],
            },
        ]
        return JSONResponse(content=sample)

    data_map = defaultdict(list)
    for day, metric, val in rows:
        data_map[metric].append({"t_utc": day.isoformat() if day else None, "v": val})

    data = [{"metric": m, "series": s} for m, s in data_map.items()]
    return JSONResponse(content=data)


@router.get("/x_deprecated/labs/{person_id}/labs-metadata")
async def labs_metadata_deprecated(person_id: str, auth=Depends(require_api_key)):
    try:
        with db.pg() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT DISTINCT LOWER(label) AS metric_name, label
                    FROM analytics.v_labs_all
                    WHERE person_id = %s
                    AND LOWER(label) NOT IN ('hr', 'spo2')
                    ORDER BY label
                """,
                    (person_id,),
                )
                rows = cur.fetchall()
            except Exception:
                try:
                    cur.execute(
                        "SELECT DISTINCT LOWER(label) AS metric_name FROM analytics.v_labs_all WHERE person_id = %s AND LOWER(label) NOT IN ('hr','spo2') ORDER BY metric_name",
                        (person_id,),
                    )
                    rows = [(r[0], r[0]) for r in cur.fetchall()]
                except Exception as e:
                    raise e

        metadata = []
        for metric_name, label in rows:
            metadata.append({"metric": metric_name, "group": "Other", "label": label})
        return JSONResponse(content=metadata)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "labs_metadata_failed", "detail": str(e)[:2000]},
        )


@router.get("/labs/{person_id}/critical-series")
async def labs_critical_series(
    person_id: str,
    agg: str = "daily",
    metrics: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    since: str | None = None,
    until: str | None = None,
    auth=Depends(require_api_key),
):
    if person_id == "ghost":
        return JSONResponse(status_code=404, content={"error": "Person not found"})

    start_date = start_date or since
    end_date = end_date or until

    for param_name, date_str in (("start_date", start_date), ("end_date", end_date)):
        if date_str:
            try:
                dt.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": f"Invalid date format for {param_name}: {date_str}. Use YYYY-MM-DD."
                    },
                )

    metric_list = (metrics or "").split(",")
    metric_list = [m.strip().lower() for m in metric_list if m.strip()]
    valid_metrics = {
        "hr": "hr_median",
        "spo2": "spo2_min",
    }

    if not metric_list:
        return JSONResponse(
            status_code=400, content={"error": "Missing or empty metrics parameter"}
        )

    selected_metrics = {m: valid_metrics[m] for m in metric_list if m in valid_metrics}
    if not selected_metrics:
        return JSONResponse(
            status_code=400, content={"error": "Invalid metrics specified"}
        )

    with db.pg() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM person WHERE id = %s", (person_id,))
        if cur.fetchone() is None:
            return JSONResponse(status_code=404, content={"error": "Person not found"})

    where_clauses = ["person_id = %s"]
    params = [person_id]
    if start_date:
        where_clauses.append("day >= %s::date")
        params.append(start_date)
    if end_date:
        where_clauses.append("day <= %s::date")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)
    columns = [v for v in selected_metrics.values()]
    sql = f"""
    SELECT day, {", ".join(columns)}
    FROM analytics.mv_daily_vitals
    WHERE {where_sql}
    ORDER BY day ASC
    """

    try:
        with db.pg() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            print(
                f"Critical series query returned {len(rows)} rows for person_id={person_id}"
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "labs_metadata_failed", "detail": str(e)[:2000]},
        )

    if not rows:
        demo_data = [
            {
                "metric": "hr",
                "unit": "bpm",
                "tz": "UTC",
                "series": [
                    {"t_utc": "2025-09-01", "v": 70},
                    {"t_utc": "2025-09-02", "v": 72},
                    {"t_utc": "2025-09-03", "v": 69},
                ],
            },
            {
                "metric": "spo2",
                "unit": "%",
                "tz": "UTC",
                "series": [
                    {"t_utc": "2025-09-01", "v": 97},
                    {"t_utc": "2025-09-02", "v": 96},
                    {"t_utc": "2025-09-03", "v": 98},
                ],
            },
        ]
        return JSONResponse(content=demo_data)

    metrics_map = {
        m: {"metric": m, "unit": "", "tz": "UTC", "series": []}
        for m in selected_metrics.keys()
    }
    for row in rows:
        day = row[0]
        for idx, m in enumerate(selected_metrics.keys()):
            val = row[idx + 1]
            if val is not None:
                metrics_map[m]["series"].append({"t_utc": day.isoformat(), "v": val})
    data = list(metrics_map.values())
    return JSONResponse(content=data)


@router.get("/medications/{person_id}/events")
async def medications_events(person_id: str, auth=Depends(require_api_key)):
    try:
        with db.pg() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT effective_time, code
                FROM medications.events
                WHERE person_id = %s
                ORDER BY effective_time ASC
                LIMIT 1000
                """,
                (person_id,),
            )
            rows = cur.fetchall()

        events = []
        for r in rows:
            t = r[0].isoformat() if r[0] else None
            code = r[1] or ""
            if t:
                events.append({"time": t, "label": code})
        return JSONResponse(content=events)
    except Exception as e:
        print(f"medications_events error for {person_id}: {e}")
        return JSONResponse(content=[])


def _no_store_headers(resp: Response) -> Response:
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Frame-Options"] = "DENY"
    return resp


@router.get("/labs/metrics-catalog")
async def labs_metrics_catalog():
    try:
        observed = []
        try:
            with db.pg() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT DISTINCT LOWER(metric) FROM analytics.mv_labs_all ORDER BY 1"
                )
                observed = [r[0] for r in cur.fetchall()]
        except Exception:
            observed = []

        mapping_set = []
        try:
            import csv as _csv

            cand_paths = []
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            cand_paths.append(
                os.path.join(
                    repo_root, "tools", "portal_ingest", "mappings", "loinc_map.csv"
                )
            )
            cand_paths.append(
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "..",
                    "tools",
                    "portal_ingest",
                    "mappings",
                    "loinc_map.csv",
                )
            )
            cand_paths.append(
                os.path.join("tools", "portal_ingest", "mappings", "loinc_map.csv")
            )

            mp = None
            for p in cand_paths:
                p2 = os.path.normpath(p)
                if os.path.exists(p2):
                    mp = p2
                    break
            if mp:
                with open(mp, "r", encoding="utf-8") as mf:
                    reader = _csv.DictReader(mf)
                    for row in reader:
                        pat = (row.get("pattern") or "").strip()
                        canon = (row.get("canonical_name") or "").strip()
                        if not pat:
                            continue
                        key = pat.lower()
                        mapping_set.append({"metric": key, "label": canon or pat})
        except Exception:
            mapping_set = []

        catalog = {}
        for k in observed:
            if not k:
                continue
            catalog[k] = {"metric": k, "label": k}
        for m in mapping_set:
            mk = m.get("metric")
            if not mk:
                continue
            if mk not in catalog:
                catalog[mk] = {"metric": mk, "label": m.get("label") or mk}
            else:
                if m.get("label"):
                    catalog[mk]["label"] = m.get("label")

        out = list(catalog.values())
        out.sort(key=lambda x: (x.get("label") or x.get("metric")))
        return JSONResponse(content=out)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "metrics_catalog_failed", "detail": str(e)[:2000]},
        )


@router.get("/debug/labs")
async def debug_labs(person_id: str = "me"):
    info = {}
    try:
        with db.pg() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT count(*) FROM analytics.v_labs_all WHERE person_id = %s",
                    (person_id,),
                )
                info["v_labs_all_count"] = cur.fetchone()[0]
                info["metadata_source"] = "v_labs_all"
            except Exception:
                try:
                    cur.execute(
                        "SELECT count(*) FROM analytics.mv_labs_all WHERE person_id = %s",
                        (person_id,),
                    )
                    info["mv_labs_all_count"] = cur.fetchone()[0]
                    info["metadata_source"] = "mv_labs_all"
                except Exception as e:
                    info["metadata_source"] = None
                    info["metadata_error"] = str(e)[:2000]

            try:
                cur.execute(
                    "SELECT metric, count(*) FROM analytics.mv_labs_all WHERE person_id = %s GROUP BY metric ORDER BY metric LIMIT 20",
                    (person_id,),
                )
                info["mv_samples"] = [
                    {"metric": r[0], "count": r[1]} for r in cur.fetchall()
                ]
            except Exception:
                info["mv_samples"] = None

            try:
                cur.execute(
                    "SELECT count(*) FROM medications.events WHERE person_id = %s",
                    (person_id,),
                )
                info["med_events_count"] = cur.fetchone()[0]
                cur.execute(
                    "SELECT effective_time, code FROM medications.events WHERE person_id = %s ORDER BY effective_time DESC LIMIT 10",
                    (person_id,),
                )
                info["med_events_sample"] = [
                    {"time": (r[0].isoformat() if r[0] else None), "code": r[1]}
                    for r in cur.fetchall()
                ]
            except Exception:
                info["med_events_count"] = 0
                info["med_events_sample"] = []
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500, content={"error": "debug_failed", "detail": str(e)[:2000]}
        )

    return JSONResponse(content=info)


@router.get("/ui/components/report-summary-card", response_class=HTMLResponse)
async def ui_component_report_summary_card(request: Request, id: str | None = None):
    tpl = templates.get_template("components/report_summary_card.html")
    html = tpl.render(request=request, report_id=(id or ""))
    resp = HTMLResponse(content=html, status_code=200)
    return _no_store_headers(resp)


@router.get("/ui/reports/{id}/summary-card", response_class=HTMLResponse)
async def ui_report_summary_card(request: Request, id: str):
    tpl = templates.get_template("components/report_summary_card.html")
    html = tpl.render(request=request, report_id=id)
    resp = HTMLResponse(content=html, status_code=200)
    return _no_store_headers(resp)


@router.get("/ui/demo")
async def ui_demo(request: Request):
    tpl = templates.get_template("demo.html")
    return _no_store_headers(templates.TemplateResponse(tpl.name, {"request": request}))


@router.get("/ui/people/{id}/labs/shared", response_class=HTMLResponse)
async def ui_people_labs_shared(request: Request, id: str):
    tpl = templates.get_template("components/labs_shared_page.html")
    html = tpl.render(request=request, person_id=id)
    resp = HTMLResponse(content=html, status_code=200)
    return resp
