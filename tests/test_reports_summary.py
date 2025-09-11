import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.routers.reports_summary import router, get_db

import pytest


@pytest.fixture(scope="function")
def app_client_and_db():
    app = FastAPI()
    app.include_router(router)

    # Single shared connection for the entire test via StaticPool
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create the view stand-in
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE report_exec_summary (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                result TEXT NOT NULL,
                signed_out_at TEXT NOT NULL
            )
        """
            )
        )

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return app, client, engine


def test_get_report_summary_200(app_client_and_db):
    app, client, engine = app_client_and_db
    rid = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            INSERT INTO report_exec_summary(id, title, result, signed_out_at)
            VALUES (:id, :title, :result, :ts)
        """
            ),
            {
                "id": rid,
                "title": "CMP",
                "result": "Negative",
                "ts": "2025-09-10T12:00:00Z",
            },
        )

    r = client.get(f"/reports/{rid}/summary")
    assert r.status_code == 200, r.text
    assert r.headers.get("Cache-Control") == "no-store"
    assert r.headers.get("content-type").startswith("application/json")
    body = r.json()
    assert set(body.keys()) == {"id", "title", "result", "signed_out_at"}
    assert body["id"] == rid
    assert body["title"] == "CMP"
    assert body["result"] == "Negative"
    assert body["signed_out_at"] == "2025-09-10T12:00:00Z"


def test_get_report_summary_404(app_client_and_db):
    app, client, _ = app_client_and_db
    rid = str(uuid.uuid4())
    r = client.get(f"/reports/{rid}/summary")
    assert r.status_code == 404
    assert r.json()["detail"] == "Not found"


def test_get_report_summary_400(app_client_and_db):
    app, client, _ = app_client_and_db
    r = client.get("/reports/not-a-uuid/summary")
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid id"
