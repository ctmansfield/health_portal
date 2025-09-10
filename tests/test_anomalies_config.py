import os, json
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_thresholds_list_and_upsert_roundtrip():
    # List existing (seeded) rows
    r = client.get("/api/anomalies/thresholds")
    assert r.status_code == 200
    before = r.json().get("rows", [])
    assert isinstance(before, list)

    # Upsert a code (tighten HR max to 210 for test)
    payload = {
        "code": "8867-4",
        "min_val": 20.0,
        "max_val": 210.0,
        "reason": "Heart rate out of range (test)",
        "enabled": True,
    }
    r2 = client.put("/api/anomalies/thresholds/8867-4", json=payload)
    assert r2.status_code == 200
    row = r2.json()["row"]
    assert row["code"] == "8867-4"
    assert abs(row["max_val"] - 210.0) < 1e-9
    assert row["enabled"] is True

    # Verify it appears in list
    r3 = client.get("/api/anomalies/thresholds")
    assert r3.status_code == 200
    rows = r3.json()["rows"]
    assert any(
        x["code"] == "8867-4" and abs((x["max_val"] or 0) - 210.0) < 1e-9 for x in rows
    )
