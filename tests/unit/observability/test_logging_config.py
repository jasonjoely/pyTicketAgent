"""Tests for root logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from pyticketagent_core.observability.json_log_formatter import JsonLogFormatter
from pyticketagent_core.observability.logging_config import configure_logging
from pyticketagent_core.observability.text_log_formatter import TextLogFormatter


@pytest.fixture(autouse=True)
def _restore_root_logger() -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)


def test_configure_logging_sets_level_and_json_formatter_by_default() -> None:
    configure_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonLogFormatter)


def test_configure_logging_selects_text_formatter() -> None:
    configure_logging("INFO", log_format="text")
    root = logging.getLogger()
    assert isinstance(root.handlers[0].formatter, TextLogFormatter)


def test_configure_logging_replaces_existing_handlers() -> None:
    configure_logging("INFO")
    configure_logging("INFO")
    assert len(logging.getLogger().handlers) == 1


def test_configure_logging_with_log_file_writes_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / "nested" / "app.log"
    configure_logging("INFO", log_file=str(log_file))

    root = logging.getLogger()
    assert len(root.handlers) == 2
    assert any(isinstance(h, logging.FileHandler) for h in root.handlers)

    root.info("hello file")
    for handler in root.handlers:
        handler.flush()

    assert log_file.exists()
    assert "hello file" in log_file.read_text(encoding="utf-8")
