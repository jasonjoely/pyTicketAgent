"""Root logging setup: console (and optionally file) output, level driven by settings."""

from __future__ import annotations

import logging
from pathlib import Path

from pyticketagent_core.observability.json_log_formatter import JsonLogFormatter
from pyticketagent_core.observability.text_log_formatter import TextLogFormatter


def configure_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: str | None = None,
) -> None:
    """Replace any existing handlers with fresh ones on the root logger.

    Without this, app-level loggers (e.g. ``pyticketagent_api.services.*``) never
    emit anything under plain ``uvicorn`` startup: uvicorn only configures its own
    ``uvicorn``/``uvicorn.access``/``uvicorn.error`` loggers, so the root logger is
    left at its default ``WARNING`` level with no handler, and INFO-level calls are
    silently dropped.

    A stream handler (stderr) is always attached. If ``log_file`` is given, a file
    handler is also attached so output is written to both places at once.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = TextLogFormatter() if log_format == "text" else JsonLogFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
