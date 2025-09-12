from starlette.testclient import TestClient
from srv.api.main import app
import app.hp_etl.db as real_db
from contextlib import contextmanager
from datetime import date

client = TestClient(app)


# Helpers to monkeypatch db.pg
@contextmanager
def fake_pg_happy(vitals_rows, person_exists=True, etl_row=None):
    class Cur:
        def __init__(self):
            self._rows = []

        def execute(self, sql, params=None):
            sql_low = sql.lower()
            if "from analytics.etl_state" in sql_low:
                # etl_row is expected to be a tuple like (json_str,)
                self._rows = [etl_row] if etl_row is not None else []
            elif "from analytics.person" in sql_low:
                self._rows = [(1,)] if person_exists else []
            else:
                self._rows = vitals_rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return self._rows

    class Conn:
        def cursor(self):
            return Cur()

    yield Conn()


def test_happy_path(monkeypatch):
    # two daily rows
    vitals = [(date(2025, 9, 1), 60, 98), (date(2025, 9, 2), 62, 97)]

    @contextmanager
    def pgctx():
        with fake_pg_happy(vitals, person_exists=True) as conn:
            yield conn

    monkeypatch.setattr(real_db, "pg", pgctx)

    r = client.get(
        "/labs/me/critical-series?metrics=hr,spo2&since=2025-09-01&until=2025-09-02"
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2
    hr = next((x for x in body if x["metric"] == "hr"), None)
    spo2 = next((x for x in body if x["metric"] == "spo2"), None)
    assert hr and "series" in hr and len(hr["series"]) == 2
    assert spo2 and "series" in spo2 and len(spo2["series"]) == 2


def test_bad_params():
    r = client.get("/labs/me/critical-series")
    assert r.status_code == 400
    r2 = client.get("/labs/me/critical-series?metrics=unknown")
    assert r2.status_code == 501
    r3 = client.get("/labs/me/critical-series?metrics=hr&since=not-a-date")
    assert r3.status_code == 400


def test_unknown_person(monkeypatch):
    vitals = []

    @contextmanager
    def pgctx():
        with fake_pg_happy(vitals, person_exists=False) as conn:
            yield conn

    monkeypatch.setattr(real_db, "pg", pgctx)
    r = client.get("/labs/ghost/critical-series?metrics=hr")
    assert r.status_code == 404
