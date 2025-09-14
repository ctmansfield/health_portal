from datetime import date
import app.hp_etl.db as real_db

from starlette.testclient import TestClient
from srv.api.main import app
from contextlib import contextmanager

client = TestClient(app)


@contextmanager
def fake_pg_full(vitals_rows, person_exists=True, etl_row=None):
    class Cur:
        def __init__(self, person_exists):
            self._rows = []
            self.person_exists = person_exists

        def execute(self, sql, params=None):
            sql_low = sql.replace("\n", " ").lower()
            print(f"Executing SQL: {sql_low} with params {params}")
            if "select 1 from person" in sql_low:
                if self.person_exists:
                    self._rows = [(1,)]
                else:
                    self._rows = []
            elif "from analytics.mv_daily_vitals" in sql_low:
                self._rows = vitals_rows
            elif "from analytics.etl_state" in sql_low:
                self._rows = [etl_row] if etl_row is not None else []
            else:
                self._rows = []

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return self._rows

    class Conn:
        def cursor(self):
            # Each call to cursor returns a new Cur instance
            return Cur(person_exists)

    yield Conn()


@contextmanager
def pgctx_badparams():
    class Cur:
        def execute(self, sql, params=None):
            if "from person" in sql.lower():
                self._rows = [(1,)]
            else:
                self._rows = []

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return self._rows

    class Conn:
        def cursor(self):
            return Cur()

    yield Conn()


def test_happy_path(monkeypatch):
    vitals = [(date(2025, 9, 1), 60, 98), (date(2025, 9, 2), 62, 97)]

    @contextmanager
    def pgctx():
        with fake_pg_full(vitals, person_exists=True) as conn:
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


def test_bad_params(monkeypatch):
    monkeypatch.setattr(real_db, "pg", pgctx_badparams)
    r = client.get("/labs/me/critical-series")
    assert r.status_code == 400
    r2 = client.get("/labs/me/critical-series?metrics=unknown")
    assert r2.status_code == 400
    r3 = client.get("/labs/me/critical-series?metrics=hr&since=not-a-date")
    assert r3.status_code == 400


def test_unknown_person(monkeypatch):
    vitals = []

    @contextmanager
    def pgctx():
        with fake_pg_full(vitals, person_exists=False) as conn:
            yield conn

    monkeypatch.setattr(real_db, "pg", pgctx)
    r = client.get("/labs/ghost/critical-series?metrics=hr")
    assert r.status_code == 404
