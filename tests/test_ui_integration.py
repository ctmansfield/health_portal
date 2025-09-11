from fastapi.testclient import TestClient
import datetime as dt
import os
from srv.api.main import app

client = TestClient(app)


class Cur:
    def __init__(self, rows, desc):
        self._rows = rows
        self.description = desc

    def execute(self, q, p=None):
        pass

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class Conn:
    def __init__(self, rows, desc):
        self._rows = rows
        self._desc = desc

    def cursor(self):
        return Cur(self._rows, self._desc)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


def make_vitals_rows():
    # day, hr_median, spo2_min
    return [(dt.date(2025, 9, 1), 70.0, 0.96), (dt.date(2025, 9, 2), 72.0, 0.95)]


def make_findings_rows():
    # metric, level, score, context, finding_time
    return [("hr", "warn", 2.5, {"note": "high"}, dt.datetime(2025, 9, 2, 12, 0))]


def make_events_rows():
    return [
        (
            "me",
            "ehr_fhir",
            "Observation",
            "LOINC",
            "8867-4",
            "Heart rate",
            dt.datetime(2025, 9, 2, 12, 0),
            105.0,
            "1/min",
            {"src": "fhir"},
        )
    ]


def fake_pg_factory(vitals_rows=None, findings_rows=None, events_rows=None):
    # will return a Conn whose cursor.fetchall returns the appropriate rows in sequence
    seq = []
    descs = []
    if vitals_rows is not None:
        seq.append(vitals_rows)
        descs.append([("day",), ("hr_median",), ("spo2_min",)])
    if findings_rows is not None:
        seq.append(findings_rows)
        descs.append(
            [("metric",), ("level",), ("score",), ("context",), ("finding_time",)]
        )
    if events_rows is not None:
        seq.append(events_rows)
        descs.append(
            [
                ("person_id",),
                ("source",),
                ("kind",),
                ("code_system",),
                ("code",),
                ("display",),
                ("effective_time",),
                ("value_num",),
                ("unit",),
                ("meta",),
            ]
        )

    class FakeCur:
        def __init__(self):
            self._i = 0
            self.description = descs[0] if descs else []

        def execute(self, q, p=None):
            # choose next dataset based on query content heuristics
            if "mv_daily_vitals" in q:
                self._i = 0
            elif "ai_findings" in q:
                self._i = 1 if len(seq) > 1 else 0
            else:
                # events
                self._i = 2 if len(seq) > 2 else 0
            self.description = descs[self._i]

        def fetchall(self):
            return seq[self._i]

        def fetchone(self):
            return seq[self._i][0] if seq[self._i] else None

    class FakeConn:
        def cursor(self):
            return FakeCur()

        def __enter__(self):
            return self

        def __exit__(self, a, b, c):
            pass

    return FakeConn


def test_dashboard_render(monkeypatch):
    vitals = make_vitals_rows()
    findings = make_findings_rows()
    monkeypatch.setenv("HP_API_KEY", "testkey")
    monkeypatch.setattr(
        "app.hp_etl.db.pg", lambda *a, **k: fake_pg_factory(vitals, findings)()
    )

    # first get login page
    r = client.get("/login")
    assert r.status_code == 200 and "Sign in" in r.text

    # post login and follow redirect
    r = client.post("/login", data={"api_key": "testkey"}, follow_redirects=True)
    assert r.status_code == 200
    # load dashboard
    r = client.get("/dashboard")
    assert r.status_code == 200
    html = r.text
    assert "Median HR" in html
    assert "Latest HR" in html
    assert "SpO2 (Daily Min)" in html


def test_events_ajax(monkeypatch):
    events = make_events_rows()
    monkeypatch.setenv("HP_API_KEY", "testkey")
    monkeypatch.setattr(
        "app.hp_etl.db.pg", lambda *a, **k: fake_pg_factory(events_rows=events)()
    )
    # login
    client.post("/login", data={"api_key": "testkey"})
    r = client.get("/dashboard/events.json?person_id=me&metric=hr&limit=5")
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j, list)
    assert len(j) == 1
    assert j[0]["value_num"] == 105.0


def test_events_page_dynamic(monkeypatch):
    events = make_events_rows()
    monkeypatch.setenv("HP_API_KEY", "testkey")
    monkeypatch.setattr(
        "app.hp_etl.db.pg", lambda *a, **k: fake_pg_factory(events_rows=events)()
    )
    client.post("/login", data={"api_key": "testkey"})
    r = client.get("/dashboard/events")
    assert r.status_code == 200
    assert "Recent Events" in r.text
    # page includes JS that calls events.json: ensure JS present
    assert "fetch" in r.text
