"""Tests for TextLogFormatter."""

from __future__ import annotations

import logging
import sys

from pyticketagent_core.observability.request_context import request_scope
from pyticketagent_core.observability.text_log_formatter import TextLogFormatter


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
    line = TextLogFormatter().format(_make_record())
    assert "INFO" in line
    assert "pyticketagent.test" in line
    assert "hello world" in line
    assert "[-]" in line


def test_format_includes_request_id_within_scope() -> None:
    with request_scope("abc123"):
        line = TextLogFormatter().format(_make_record())
    assert "[abc123]" in line


def test_format_includes_extra_fields_as_key_value_pairs() -> None:
    record = _make_record(event="assist.prompt", model="gpt-4")
    line = TextLogFormatter().format(record)
    assert "event='assist.prompt'" in line
    assert "model='gpt-4'" in line


def test_format_includes_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _make_record()
        record.exc_info = sys.exc_info()

    line = TextLogFormatter().format(record)
    assert "ValueError: boom" in line
