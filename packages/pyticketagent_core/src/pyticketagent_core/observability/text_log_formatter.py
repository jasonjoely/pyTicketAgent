"""Human-readable log formatter: one line per record, with request correlation and extras."""

from __future__ import annotations

import logging

from pyticketagent_core.observability.request_context import get_request_id

_RESERVED_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class TextLogFormatter(logging.Formatter):
    """Render each log record as one readable line, including ``extra=`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        line = (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} "
            f"{record.levelname:<8} "
            f"[{get_request_id()}] "
            f"{record.name}: {record.getMessage()}"
        )

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED_RECORD_ATTRS
        }
        if extras:
            line += " " + " ".join(f"{key}={value!r}" for key, value in extras.items())

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line
