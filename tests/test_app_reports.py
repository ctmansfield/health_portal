from fastapi.testclient import TestClient
import json
import uuid
from srv.api.main import app
import datetime as dt

client = TestClient(app)


class FakeCur:
    def __init__(self, rows, desc):
        self._rows = rows
        self.description = desc

    def execute(self, q, p=None):
        pass

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, rows, desc):
        self._cur = FakeCur(rows, desc)

    def cursor(self):
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


def fake_pg_factory_single(payload):
    # payload should be a Python dict representing JSONB
    rows = [(payload,)]
    desc = [("payload",)]

    def factory(*a, **k):
        return FakeConn(rows, desc)

    return factory


def test_get_report_success(monkeypatch):
    payload = {"report": "ok", "value": 123}
    monkeypatch.setattr("app.hp_etl.db.pg", fake_pg_factory_single(payload))
    # create a uuid
    rid = str(uuid.uuid4())
    r = client.get(f"/reports/{rid}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers.get("cache-control") == "no-store"
    assert r.json() == payload


def test_get_report_not_found(monkeypatch):
    # simulate no rows
    def factory(*a, **k):
        return FakeConn([], [])

    monkeypatch.setattr("app.hp_etl.db.pg", factory)
    rid = str(uuid.uuid4())
    r = client.get(f"/reports/{rid}")
    assert r.status_code == 404
    assert r.json().get("detail") == "Report not found"


def test_get_report_bad_uuid():
    r = client.get("/reports/not-a-uuid")
    assert r.status_code == 400
    assert r.json().get("detail") == "invalid id format"
