from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_anomalies_ok():
    r = client.get("/api/vitals/anomalies", params={"days": 7, "limit": 5})
    assert r.status_code == 200
    js = r.json()
    assert "rows" in js
    assert isinstance(js["rows"], list)
