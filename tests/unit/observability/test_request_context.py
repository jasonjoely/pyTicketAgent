"""Tests for request-scoped correlation IDs."""

from __future__ import annotations

from pyticketagent_core.observability.request_context import get_request_id, request_scope


def test_default_request_id_outside_scope() -> None:
    assert get_request_id() == "-"


def test_request_scope_generates_id_when_none_given() -> None:
    with request_scope() as request_id:
        assert request_id != "-"
        assert get_request_id() == request_id
    assert get_request_id() == "-"


def test_request_scope_uses_given_id() -> None:
    with request_scope("fixed-id") as request_id:
        assert request_id == "fixed-id"
        assert get_request_id() == "fixed-id"


def test_nested_scopes_restore_previous_id() -> None:
    with request_scope("outer"):
        with request_scope("inner"):
            assert get_request_id() == "inner"
        assert get_request_id() == "outer"
