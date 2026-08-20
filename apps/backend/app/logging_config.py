"""Central logging setup: console + rotating files under ``logs/``.

Call :func:`setup_logging` once at process start (done in ``app.api`` and
``app.ocr.providers._shared`` so it also covers direct pipeline/test runs).
All app loggers live under the ``app`` namespace and propagate to it; the LLM
request/response logger additionally gets its own file so provider traffic
can be inspected without wading through the rest of the pipeline's logs.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = BACKEND_ROOT / "logs"

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

_configured = False
_llm_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger("app")
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)
    root.propagate = False


def get_llm_logger() -> logging.Logger:
    """Logger for outgoing/incoming vision LLM traffic, also written to logs/llm.log."""
    global _llm_configured
    setup_logging()
    logger = logging.getLogger("app.llm")
    if not _llm_configured:
        _llm_configured = True
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_DIR / "llm.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
    return logger
