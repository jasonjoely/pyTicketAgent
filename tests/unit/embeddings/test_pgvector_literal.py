"""Tests for pgvector text literal formatting."""

from pyticketagent_core.embeddings.pgvector_literal import format_pgvector_literal


def test_format_none() -> None:
    assert format_pgvector_literal(None) is None


def test_format_vector() -> None:
    assert format_pgvector_literal([1.0, 2.5, -0.25]) == "[1.0,2.5,-0.25]"
