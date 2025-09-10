from fastapi.testclient import TestClient
from srv.api.main import app

client = TestClient(app)


class Cur:
    def __init__(self, rows, desc):
        self._rows = rows
        self.description = desc

    def execute(self, q, p=None):
        # ignore the SQL; return everything
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


def test_events_json_app_layer_filter_and_limit(monkeypatch):
    # create many rows that include mixed codes; our handler should filter to hr and apply limit
    rows = [
        (
            "me",
            "ehr_fhir",
            "Observation",
            "LOINC",
            "8867-4",
            "Heart rate",
            None,
            100.0,
            "1/min",
            {},
        ),
    ] * 10
    desc = [
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
    monkeypatch.setenv("HP_API_KEY", "testkey")
    monkeypatch.setattr("app.hp_etl.db.pg", lambda *a, **k: Conn(rows, desc))

    # login
    client.post("/login", data={"api_key": "testkey"})
    # request with limit=3
    r = client.get("/dashboard/events.json?person_id=me&metric=hr&limit=3")
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j, list)
    assert len(j) == 3
    for item in j:
        assert item["code"] == "8867-4"
