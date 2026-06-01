"""
observability/logging_config.py — Structured JSON logging.

Étape 11 — Observabilité
─────────────────────────
Configures Python's logging to:
  1. Output JSON-formatted log lines (machine-parseable)
  2. Include trace_id from contextvars (set by TracingMiddleware)
  3. Include service name, version, and environment
  4. Route logs to stdout (12-factor app compatible)

Usage:
    from app.observability.logging_config import setup_logging
    setup_logging()  # call once at app startup
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# ─── Trace context ────────────────────────────────────────────────────────

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
"""Correlation ID set per-request by TracingMiddleware."""

# ─── JSON formatter ───────────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with trace_id propagation."""

    def __init__(self, service: str = "ravinala-backend", version: str = "1.0.0"):
        super().__init__()
        self.service = service
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
            "version": self.version,
            "trace_id": trace_id_var.get("-"),
        }
        if record.exc_info and record.exc_info[1] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        # Merge any extra fields passed via logger.info("msg", extra={...})
        for key in ("component", "ticker", "duration_ms", "cache_hit",
                     "data_quality", "endpoint", "status_code"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        return json.dumps(entry, default=str)


# ─── Setup function ───────────────────────────────────────────────────────

def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """
    Configure root logger.

    Parameters
    ----------
    level : str
        Logging level (DEBUG, INFO, WARNING, ERROR).
    json_format : bool
        If True, use JSON formatter. If False, use standard human-readable format.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates on re-call
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(root.level)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ))

    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "yfinance", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
