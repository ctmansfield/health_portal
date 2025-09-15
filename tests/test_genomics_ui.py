from fastapi.testclient import TestClient
from srv.api.main import app

client = TestClient(app)


class Cur:
    def __init__(self, data):
        self._data = data
        self.description = [
            ("report_id",),
            ("person_id",),
            ("filename",),
            ("path",),
            ("generated_at",),
        ]

    def execute(self, q, p=None):
        pass

    def fetchall(self):
        return self._data

    def fetchone(self):
        return self._data[0] if self._data else None


class Conn:
    def __init__(self, data):
        self._data = data

    def cursor(self):
        return Cur(self._data)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


def test_genomics_index(monkeypatch, tmp_path):
    # create fake report file
    f = tmp_path / "r1.pdf"
    f.write_text("pdf")
    sample = [("r1", "p1", "r1.pdf", str(f), "2025-09-01T00:00:00Z")]
    monkeypatch.setattr("app.hp_etl.db.pg", lambda *a, **k: Conn(sample))
    r = client.get("/genomics")
    assert r.status_code == 200
    assert "Available Reports" in r.text
    assert "r1.pdf" in r.text


def test_genomics_download(monkeypatch, tmp_path):
    f = tmp_path / "r2.pdf"
    f.write_text("pdf")
    sample = [("r2", "p2", "r2.pdf", str(f), "2025-09-01T00:00:00Z")]
    monkeypatch.setattr("app.hp_etl.db.pg", lambda *a, **k: Conn(sample))
    r = client.get("/genomics/reports/r2/download")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application")
