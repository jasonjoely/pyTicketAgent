"""Tests for embedding content hashing."""

from pyticketagent_core.embeddings.embedding_content_hasher import (
    EmbeddingContentHasher,
)


def test_hash_is_stable_sha256_hex() -> None:
    hasher = EmbeddingContentHasher()
    first = hasher.hash_text("hello")
    second = hasher.hash_text("hello")
    assert first == second
    assert len(first) == 64
    assert first != hasher.hash_text("hello!")
