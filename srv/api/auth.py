import os
from fastapi import Header, HTTPException, Request
from typing import Optional


def require_api_key(request: Request, x_api_key: Optional[str] = Header(None)):
    """FastAPI dependency to require HP_API_KEY if set.
    Checks X-API-Key header first, then cookie 'hp_api_key'.
    Reads the HP_API_KEY from the environment at call time so test monkeypatching works.
    """
    hp_api_key = os.environ.get("HP_API_KEY")
    if not hp_api_key:
        return True
    # header takes precedence
    if x_api_key and x_api_key == hp_api_key:
        return True
    # check cookie
    cookie_key = request.cookies.get("hp_api_key")
    if cookie_key and cookie_key == hp_api_key:
        return True
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
