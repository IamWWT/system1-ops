"""JSON service logs with correlation IDs and complete exception evidence."""

import datetime
import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        value: dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, datetime.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        correlation = re.search(r"request_id=([^\s;]+)", message)
        if correlation:
            value["request_id"] = correlation.group(1)
        for name in ("request_id", "client", "actor", "method", "path", "http_status", "latency_ms"):
            if hasattr(record, name):
                value[name] = getattr(record, name)
        if record.exc_info:
            value["exception"] = self.formatException(record.exc_info)
        return json.dumps(value, ensure_ascii=False)


def configure_logging(path: Path, settings: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=settings["log_max_bytes"], backupCount=settings["log_backups"], encoding="utf-8"
    )
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=settings["log_level"], handlers=[handler], force=True)
    logging.captureWarnings(True)
