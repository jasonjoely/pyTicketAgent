"""Tests for AssistRequest embedding_space field."""

import pytest
from pydantic import ValidationError

from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_api.models.assist_request import AssistRequest


def test_assist_request_accepts_embedding_space() -> None:
    request = AssistRequest(
        question="Redis timeouts",
        embedding_space=EmbeddingSpace.FASTEMBED,
    )
    assert request.embedding_space == EmbeddingSpace.FASTEMBED


def test_assist_request_embedding_space_optional() -> None:
    request = AssistRequest(question="Redis timeouts")
    assert request.embedding_space is None


def test_assist_request_rejects_invalid_embedding_space() -> None:
    with pytest.raises(ValidationError):
        AssistRequest.model_validate(
            {"question": "x", "embedding_space": "not-a-space"}
        )
