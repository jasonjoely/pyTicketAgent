"""Tests for JsonLogFormatter."""

from __future__ import annotations

import json
import logging
import sys

from pyticketagent_core.observability.json_log_formatter import JsonLogFormatter
from pyticketagent_core.observability.request_context import request_scope


def _make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="pyticketagent.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_format_includes_core_fields() -> None:
    payload = json.loads(JsonLogFormatter().format(_make_record()))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "pyticketagent.test"
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "-"
    assert "timestamp" in payload


def test_format_includes_request_id_within_scope() -> None:
    with request_scope("abc123"):
        payload = json.loads(JsonLogFormatter().format(_make_record()))
    assert payload["request_id"] == "abc123"


def test_format_promotes_extra_fields() -> None:
    record = _make_record(event="assist.prompt", model="gpt-4")
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["event"] == "assist.prompt"
    assert payload["model"] == "gpt-4"


def test_format_includes_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _make_record()
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonLogFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]
