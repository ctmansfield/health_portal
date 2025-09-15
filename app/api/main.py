from srv.api.logging_setup import configure_logging
from fastapi.responses import HTMLResponse
from srv.api.middleware.reqlog import RequestLogMiddleware
import logging
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import os
from hp_etl.db import pg, dsn_from_env

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Health Portal API")


app.add_middleware(RequestLogMiddleware)


@app.get("/", include_in_schema=False)
def root():
    # send humans to docs
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    dsn = os.getenv("HP_DSN", dsn_from_env())
    # simple DB check
    try:
        with pg(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/events/latest")
def latest_events(limit: int = 10):
    dsn = os.getenv("HP_DSN", dsn_from_env())
    with pg(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT person_id, source, kind, code_system, code,
                   value_num, unit, effective_time
            FROM analytics.data_events
            ORDER BY effective_time DESC NULLS LAST
            LIMIT %s
        """,
            (limit,),
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@app.get("/ui/people/{person_id}/labs/critical")
async def labs_critical(person_id: str):
    html = (
        "<!doctype html><html><body><main><h1>Critical Labs</h1></main></body></html>"
    )
    return HTMLResponse(html, status_code=200)
