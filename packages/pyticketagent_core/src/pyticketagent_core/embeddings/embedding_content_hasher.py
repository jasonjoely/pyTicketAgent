"""Content hashing for embedding skip / re-embed decisions."""

from __future__ import annotations

import hashlib


class EmbeddingContentHasher:
    """SHA-256 hex digest of embed text (UTF-8)."""

    def hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
