from fastapi import FastAPI
from .routers.anomalies import router as anomalies_router
from .routers.anomaly_config import router as anomaly_config_router


from .routers.vitals import router as vitals_router
from fastapi.middleware.cors import CORSMiddleware
from .routers.summary import router as summary_router
from .routers.events import router as events_router
from .routers.exports import router as exports_router

app = FastAPI(title="Health Portal API")
app.include_router(anomaly_config_router, prefix="/api")

# Permissive CORS for local/dev; tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summary_router, prefix="/api")
app.include_router(vitals_router, prefix="/api")
app.include_router(anomalies_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(exports_router, prefix="/api")


@app.get("/")
def root():
    return {"ok": True, "service": "health_portal"}
