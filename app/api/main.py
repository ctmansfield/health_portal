from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.summary import router as summary_router
from .routers.events import router as events_router
from .routers.exports import router as exports_router

app = FastAPI(title="Health Portal API")

# Permissive CORS for local/dev; tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summary_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(exports_router, prefix="/api")


@app.get("/")
def root():
    return {"ok": True, "service": "health_portal"}
