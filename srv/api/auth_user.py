from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import app.hp_etl.db as db
from app.hp_etl.csrf import generate_csrf, require_csrf
from passlib.context import CryptContext
import secrets, os, datetime as dt

router = APIRouter()
templates = Jinja2Templates(directory="srv/api/templates")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE = "hp_sess"


def create_session(conn, user_id, ttl_hours=12):
    sid = secrets.token_urlsafe(32)
    expires_dt = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=ttl_hours)
    expires = expires_dt.isoformat().replace("+00:00", "Z")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO analytics.sessions(session_id, user_id, expires_at) VALUES (%s,%s,%s)",
        (sid, user_id, expires),
    )
    # if redis is configured, mirror session for fast lookup
    try:
        from app.hp_etl.session_store import set_redis_session

        set_redis_session(sid, user_id, expires)
    except Exception:
        pass
    return sid, expires


def get_user_by_username(conn, username):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash, disabled FROM analytics.users WHERE username = %s",
        (username,),
    )
    return cur.fetchone()


@router.post("/auth/login")
async def login(request: Request):
    # support both form-encoded and JSON bodies
    try:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    except Exception:
        try:
            j = await request.json()
            username = j.get("username") if isinstance(j, dict) else None
            password = j.get("password") if isinstance(j, dict) else None
        except Exception:
            username = password = None
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    with db.pg() as conn:
        row = get_user_by_username(conn, username)
        if not row:
            raise HTTPException(status_code=401, detail="invalid credentials")
        user_id, uname, phash, disabled = row
        if disabled:
            raise HTTPException(status_code=403, detail="user disabled")
        if not pwd_ctx.verify(password, phash):
            raise HTTPException(status_code=401, detail="invalid credentials")
        sid, expires = create_session(conn, user_id)
    resp = JSONResponse({"session": sid, "expires": expires})
    resp.set_cookie(SESSION_COOKIE, sid, httponly=True, samesite="Lax", path="/")
    # set a CSRF double-submit cookie readable by JS (so clients can send X-CSRF-Token)
    try:
        generate_csrf(resp)
    except Exception:
        # best-effort; don't fail login if CSRF cookie can't be set
        pass
    return resp


@router.post("/auth/logout")
def logout(request: Request, csrf=Depends(require_csrf)):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        try:
            from app.hp_etl.session_store import delete_redis_session

            delete_redis_session(sid)
        except Exception:
            pass
        with db.pg() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM analytics.sessions WHERE session_id = %s", (sid,))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    # clear csrf cookie as well
    resp.delete_cookie("hp_csrf", path="/")
    return resp


def get_current_user(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        # fallback to API key
        key = request.headers.get("x-api-key") or request.cookies.get("hp_api_key")
        hp = os.environ.get("HP_API_KEY")
        if hp and key == hp:
            return {"system": True, "roles": ["admin"]}
        raise HTTPException(status_code=401, detail="not authenticated")
    # try redis-backed session first for performance
    try:
        from app.hp_etl.session_store import get_redis_session, delete_redis_session

        r = get_redis_session(sid)
        if r:
            user_id, expires_at = r
            # note: expires_at likely ISO Z string
        else:
            with db.pg() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT user_id, expires_at FROM analytics.sessions WHERE session_id = %s",
                    (sid,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=401, detail="invalid session")
                user_id, expires_at = row
    except Exception:
        # fallback to DB if redis check fails
        with db.pg() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, expires_at FROM analytics.sessions WHERE session_id = %s",
                (sid,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="invalid session")
            user_id, expires_at = row
        # check expires (accept timestamptz or ISO Z string)
        try:
            if isinstance(expires_at, str):
                expires_dt = dt.datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
            else:
                expires_dt = expires_at
            now_dt = dt.datetime.now(dt.timezone.utc)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=dt.timezone.utc)
            if expires_dt < now_dt:
                cur.execute(
                    "DELETE FROM analytics.sessions WHERE session_id = %s", (sid,)
                )
                raise HTTPException(status_code=401, detail="session expired")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="invalid session")

        cur.execute(
            "SELECT id, username, email, full_name, disabled FROM analytics.users WHERE id = %s",
            (user_id,),
        )
        u = cur.fetchone()
        if not u:
            raise HTTPException(status_code=401, detail="user not found")
        uid, username, email, full_name, disabled = u
        if disabled:
            raise HTTPException(status_code=403, detail="user disabled")
        # fetch roles
        cur.execute(
            "SELECT r.name FROM analytics.roles r JOIN analytics.user_roles ur ON ur.role_id = r.id WHERE ur.user_id = %s",
            (user_id,),
        )
        roles = [r[0] for r in cur.fetchall()]
        return {
            "id": uid,
            "username": username,
            "email": email,
            "full_name": full_name,
            "roles": roles,
        }


def require_role(*roles):
    def dep(request: Request):
        # In developer mode (no HP_API_KEY configured) allow access for convenience.
        hp = os.environ.get("HP_API_KEY")
        if not hp:
            return {"system": True, "roles": ["admin"]}
        # otherwise resolve current user and enforce roles
        user = get_current_user(request)
        if user.get("system"):
            return user
        user_roles = set(user.get("roles", []))
        if not any(r in user_roles for r in roles):
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return dep


# Admin session management endpoints
@router.get("/admin/sessions")
def admin_list_sessions(
    auth=Depends(require_role("admin")),
    page: int = 1,
    per_page: int = 50,
    user_id: str | None = None,
):
    """Return recent sessions (session_id, user_id, expires_at, created_at) with pagination and optional user filter."""
    offset = (max(1, page) - 1) * max(1, per_page)
    items = []
    where = []
    params = []
    if user_id:
        where.append("user_id = %s")
        params.append(user_id)
    q_where = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT session_id, user_id, expires_at, created_at FROM analytics.sessions {q_where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    with db.pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            for r in rows:
                items.append(dict(zip(cols, r)))
        except Exception:
            items = []
    return {"sessions": items, "page": page, "per_page": per_page}


@router.post("/admin/sessions/{session_id}/revoke")
def admin_revoke_session(
    session_id: str, auth=Depends(require_role("admin")), csrf=Depends(require_csrf)
):
    sql = "DELETE FROM analytics.sessions WHERE session_id = %s"
    try:
        from app.hp_etl.session_store import delete_redis_session

        delete_redis_session(session_id)
    except Exception:
        pass
    with db.pg() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, (session_id,))
            # optional: check rowcount
        except Exception:
            return {"ok": False, "error": "failed"}
    return {"ok": True}


@router.get("/admin/sessions/ui", response_class=HTMLResponse)
def admin_sessions_ui(request: Request, auth=Depends(require_role("admin"))):
    # Render admin sessions UI page
    return templates.TemplateResponse(
        request, "admin_sessions.html", {"request": request}
    )
