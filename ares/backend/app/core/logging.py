"""Structured logging for the ARES Platform."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class AresJsonFormatter(logging.Formatter):
    """Format logs as structured JSON avoiding emission of sensitive fields."""

    SENSITIVE_KEYS = {"password", "token", "secret", "private_key", "authorization", "key", "signature"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Contextual extra fields
        for field in ("request_id", "actor_id", "device_id", "assessment_id", "service"):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = str(val)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("ares")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for h in list(logger.handlers):
        logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(AresJsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()
