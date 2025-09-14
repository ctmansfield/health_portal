import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import dashboard, dashboard_events, genomics
from .v1 import __init__ as v1pkg
from .reports import router as reports_router

app = FastAPI()

# Mount static files (single mount)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# include routers
app.include_router(dashboard.router)
app.include_router(dashboard_events.router)
app.include_router(genomics.router)
app.include_router(reports_router)

# include v1 api if present
try:
    from .v1 import events, findings, genomics as v1_gen

    app.include_router(events.router)
    app.include_router(findings.router)
    app.include_router(v1_gen.router)
except Exception:
    pass


# healthz
@app.get("/healthz")
def healthz():
    return {"ok": True}
