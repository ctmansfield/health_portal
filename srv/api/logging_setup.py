import os
import logging
from logging.handlers import RotatingFileHandler

OUTDIR = os.environ.get("HP_LOG_DIR", "/mnt/nas_storage/outgoing")
os.makedirs(OUTDIR, exist_ok=True)


def _mk_handler(path):
    h = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    h.setFormatter(fmt)
    h.setLevel(logging.INFO)
    return h


def configure_logging():
    # hp.request -> requests logfile
    req_logger = logging.getLogger("hp.request")
    if not any(
        isinstance(h, RotatingFileHandler) and getattr(h, "_hp_tag", "") == "req"
        for h in req_logger.handlers
    ):
        h1 = _mk_handler(os.path.join(OUTDIR, "health-portal-requests.log"))
        h1._hp_tag = "req"
        req_logger.addHandler(h1)
        req_logger.setLevel(logging.INFO)
        req_logger.propagate = True  # still print to console

    # uvicorn + app errors -> general logfile
    err_logger = logging.getLogger("uvicorn.error")
    if not any(
        isinstance(h, RotatingFileHandler) and getattr(h, "_hp_tag", "") == "uvicorn"
        for h in err_logger.handlers
    ):
        h2 = _mk_handler(os.path.join(OUTDIR, "health-portal-uvicorn.log"))
        h2._hp_tag = "uvicorn"
        err_logger.addHandler(h2)
        err_logger.setLevel(logging.INFO)
        err_logger.propagate = True

    access_logger = logging.getLogger("uvicorn.access")
    if not any(
        isinstance(h, RotatingFileHandler) and getattr(h, "_hp_tag", "") == "access"
        for h in access_logger.handlers
    ):
        h3 = _mk_handler(os.path.join(OUTDIR, "health-portal-access.log"))
        h3._hp_tag = "access"
        access_logger.addHandler(h3)
        access_logger.setLevel(logging.INFO)
        access_logger.propagate = True
