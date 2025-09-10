from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_vitals_latest_ok():
    r = client.get("/api/vitals/latest")
    assert r.status_code == 200
    assert "rows" in r.json()


def test_vitals_daily_ok():
    r = client.get("/api/vitals/daily", params={"days": 3})
    assert r.status_code == 200
    assert "rows" in r.json()
