from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from app.hp_etl.db import pg
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
    return sid, expires


def get_user_by_username(conn, username):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash, disabled FROM analytics.users WHERE username = %s",
        (username,),
    )
    return cur.fetchone()


@router.post("/auth/login")
def login(req: Request):
    data = req.json() if hasattr(req, "json") else {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    with pg() as conn:
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
    return resp


@router.post("/auth/logout")
def logout(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        with pg() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM analytics.sessions WHERE session_id = %s", (sid,))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
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
    with pg() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, expires_at FROM analytics.sessions WHERE session_id = %s",
            (sid,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="invalid session")
        user_id, expires_at = row
        # TODO: check expires
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
    def dep(user=Depends(get_current_user)):
        if user.get("system"):
            return user
        user_roles = set(user.get("roles", []))
        if not any(r in user_roles for r in roles):
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return dep
