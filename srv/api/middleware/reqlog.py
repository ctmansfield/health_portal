import os
import time
import uuid
import json
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("hp.request")


def _emit(ctx: dict):
    fmt = os.getenv("HP_REQLOG_FORMAT", "text").lower()
    if fmt == "json":
        try:
            logger.info(json.dumps(ctx, default=str))
        except Exception:
            logger.info("log_json_error=%s fallback_text=%s", ctx.get("error", ""), ctx)
    else:
        line = (
            "req={req} method={method} path={path} query={query} status={status} "
            "dur_ms={dur_ms:.2f} bytes={bytes} user={user} ua={ua}"
        ).format(**ctx)
        if ctx.get("error"):
            line += f" error={ctx['error']}"
            logger.error(line)
        else:
            logger.info(line)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Request/response logging with timing and correlation id (X-Request-ID)."""

    async def dispatch(self, request: Request, call_next: Callable):
        start = time.perf_counter()
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        user = getattr(request.state, "user", None)
        user_id = getattr(user, "id", None)
        ctx = {
            "ts": time.time(),
            "req": req_id,
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query or "-",
            "status": None,
            "dur_ms": 0.0,
            "bytes": "-",
            "user": user_id,
            "ua": request.headers.get("user-agent", "-"),
            "error": None,
        }
        try:
            response = await call_next(request)
            ctx["dur_ms"] = (time.perf_counter() - start) * 1000.0
            ctx["status"] = response.status_code
            ctx["bytes"] = response.headers.get("content-length", "-")
            _emit(ctx)
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception as e:
            ctx["dur_ms"] = (time.perf_counter() - start) * 1000.0
            ctx["status"] = 500
            ctx["error"] = str(e)
            _emit(ctx)
            logger.exception("stacktrace for req=%s", req_id)
            raise
