from srv.api.auth_user import create_session, get_current_user
from fastapi import HTTPException
import datetime as dt


class FakeCursor:
    def __init__(self, behavior):
        self.behavior = behavior
        self._last_q = None
        self._last_params = None

    def execute(self, q, params=None):
        self._last_q = q
        self._last_params = params
        # record inserts to sessions
        if q.strip().upper().startswith("INSERT INTO ANALYTICS.SESSIONS"):
            # params = (sid, user_id, expires)
            self.behavior.setdefault("inserted_sessions", []).append(tuple(params))
        if q.strip().upper().startswith("DELETE FROM ANALYTICS.SESSIONS"):
            # record deletes
            self.behavior.setdefault("deleted_sessions", []).append(tuple(params or ()))

    def fetchone(self):
        q = (self._last_q or "").upper()
        if "FROM ANALYTICS.SESSIONS" in q:
            return self.behavior.get("session_row")
        if "FROM ANALYTICS.USERS" in q:
            return self.behavior.get("user_row")
        return None

    def fetchall(self):
        q = (self._last_q or "").upper()
        if "FROM ANALYTICS.ROLES" in q:
            return self.behavior.get("roles_rows", [])
        return []


class FakeConn:
    def __init__(self, behavior):
        self.behavior = behavior

    def cursor(self):
        return FakeCursor(self.behavior)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


def test_create_session_inserts_row():
    behavior = {}
    conn = FakeConn(behavior)
    sid, expires = create_session(conn, user_id=42, ttl_hours=1)
    assert isinstance(sid, str) and len(sid) > 8
    assert "inserted_sessions" in behavior
    ins = behavior["inserted_sessions"][0]
    assert ins[0] == sid
    assert ins[1] == 42
    assert ins[2].endswith("Z")


def test_get_current_user_expired_session():
    # session expired in the past
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
    behavior = {"session_row": (123, past.isoformat().replace("+00:00", "Z"))}
    conn = FakeConn(behavior)
    # monkeypatch pg to return this conn
    import app.hp_etl.db as db

    orig_pg = db.pg

    try:
        db.pg = lambda *a, **k: conn

        class Req:  # minimal request stub
            cookies = {"hp_sess": "s1", "hp_api_key": None}

        try:
            get_current_user(Req())
            assert False, "expected HTTPException due to expired session"
        except HTTPException as e:
            assert e.status_code == 401
            assert "expired" in e.detail or "invalid" in e.detail
        # ensure deletion was attempted
        assert "deleted_sessions" in behavior
    finally:
        db.pg = orig_pg


def test_get_current_user_valid_session():
    # session expires in future
    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    behavior = {
        "session_row": (123, future.isoformat().replace("+00:00", "Z")),
        "user_row": (123, "alice", "a@b", "Alice", False),
        "roles_rows": [("clinician",)],
    }
    conn = FakeConn(behavior)
    import app.hp_etl.db as db

    orig_pg = db.pg

    try:
        db.pg = lambda *a, **k: conn

        class Req:
            cookies = {"hp_sess": "s2", "hp_api_key": None}

        user = get_current_user(Req())
        assert user["username"] == "alice"
        assert "clinician" in user["roles"]
    finally:
        db.pg = orig_pg
