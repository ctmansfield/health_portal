from fastapi.testclient import TestClient
from srv.api.main import app
import datetime as dt

client = TestClient(app)


class Cur:
    def __init__(self, rows, desc):
        self._rows = rows
        self.description = desc
        self.rowcount = 0

    def execute(self, q, p=None):
        self.rowcount = 1

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


def test_admin_sessions_list_and_revoke(monkeypatch):
    # sample session row
    rows = [("s1", 1, "2025-09-10T12:00:00Z", "2025-09-10T00:00:00Z")]
    desc = [("session_id",), ("user_id",), ("expires_at",), ("created_at",)]
    conn = Conn(rows, desc)
    # monkeypatch db.pg used by auth_user and other modules
    import app.hp_etl.db as db

    orig_pg = db.pg
    try:
        db.pg = lambda *a, **k: conn
        # monkeypatch HP_API_KEY so require_role sees system admin
        import os

        os.environ["HP_API_KEY"] = "testkey"
        # call list (no auth required because HP_API_KEY is set, fallback behaves as system admin)
        r = client.get("/admin/sessions")
        assert r.status_code == 200
        j = r.json()
        assert isinstance(j.get("sessions"), list)

        # revoke
        r2 = client.post("/admin/sessions/s1/revoke")
        assert r2.status_code == 200
        assert r2.json().get("ok") is True
    finally:
        db.pg = orig_pg
        try:
            del os.environ["HP_API_KEY"]
        except Exception:
            pass
