"""Structured logging. Never logs secrets or access tokens."""
import logging
import sys

_SECRET_HINTS = ("key", "secret", "token", "password", "authorization")


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def safe_extra(data: dict) -> dict:
    """Redact any obviously-sensitive keys before logging."""
    out = {}
    for k, v in data.items():
        if any(h in k.lower() for h in _SECRET_HINTS):
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out
