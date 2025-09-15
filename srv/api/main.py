import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import dashboard, dashboard_events, genomics
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


# favicon route
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("srv/api/static/favicon.ico")


# healthz
@app.get("/healthz")
def healthz():
    return {"ok": True}


# optional labs router
try:
    from .labs_api import router as labs_router

    app.include_router(labs_router)
except Exception:
    pass

# optional records router
try:
    from .records_api import router as records_router

    app.include_router(records_router)
except Exception:
    pass
