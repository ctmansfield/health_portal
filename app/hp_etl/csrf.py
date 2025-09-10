"""Simple double-submit CSRF helpers.

This implements a minimal double-submit cookie pattern:
- generate_csrf(response) -> creates a random token and sets a non-HttpOnly cookie 'hp_csrf'.
- require_csrf(request) -> FastAPI dependency that verifies header X-CSRF-Token matches cookie hp_csrf.

Note: This is suitable for same-site protections and intranet deployments. For stronger CSRF protections
consider SameSite=Strict and a server-side token store.
"""

from fastapi import Request, Response, HTTPException
import secrets
from typing import Optional

CSRF_COOKIE_NAME = "hp_csrf"
CSRF_HEADER = "x-csrf-token"


def generate_csrf(resp: Response, ttl_seconds: int = 3600) -> str:
    """Generate a CSRF token, set as non-HttpOnly cookie so client JS can read it.
    Returns the token so callers can include it in responses if desired.
    """
    token = secrets.token_urlsafe(32)
    # set cookie readable by JS (httponly=False) so client can read and send header
    resp.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,
        samesite="Lax",
        path="/",
        max_age=ttl_seconds,
    )
    return token


async def require_csrf(request: Request) -> bool:
    """FastAPI dependency: verifies that the X-CSRF-Token header matches the hp_csrf cookie."""
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header:
        raise HTTPException(status_code=403, detail="CSRF token missing")
    if header != cookie:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
    return True
