"""Reciprocal Rank Fusion for merging ranked retrieval lists."""

from __future__ import annotations

from collections.abc import Sequence


class RrfRankFusion:
    """Fuse ranked ID lists with Reciprocal Rank Fusion (RRF)."""

    def __init__(self, k: int = 60) -> None:
        if k < 0:
            raise ValueError("RRF k must be non-negative.")
        self._k = k

    def fuse(self, *ranked_id_lists: Sequence[int]) -> list[int]:
        """Return unique IDs ordered by descending RRF score.

        Ties break by lower ID. Rank is 1-based within each list.
        """
        scores: dict[int, float] = {}
        for ranked_ids in ranked_id_lists:
            for rank, item_id in enumerate(ranked_ids, start=1):
                scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (self._k + rank)

        return sorted(scores.keys(), key=lambda item_id: (-scores[item_id], item_id))
