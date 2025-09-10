import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import dashboard_events, genomics
from .v1 import __init__ as v1pkg

app = FastAPI()

# Mount static
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

# include routers
from . import dashboard

app.include_router(dashboard.router)
app.include_router(dashboard_events.router)
app.include_router(genomics.router)
# include v1 api if present
try:
    from .v1 import events, findings, genomics as v1_gen

    app.include_router(events.router)
    app.include_router(findings.router)
    app.include_router(v1_gen.router)
except Exception:
    pass


# auth user routes
try:
    from . import auth_user

    app.include_router(auth_user.router)
except Exception:
    pass


# healthz
@app.get("/healthz")
def healthz():
    return {"ok": True}
