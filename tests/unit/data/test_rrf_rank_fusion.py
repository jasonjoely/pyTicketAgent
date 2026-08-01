"""Tests for Reciprocal Rank Fusion."""

from pyticketagent_core.data.rrf_rank_fusion import RrfRankFusion


def test_fuse_prefers_items_ranked_high_in_both_lists() -> None:
    fused = RrfRankFusion(k=60).fuse([2, 1, 3], [2, 4, 1])
    assert fused[0] == 2
    assert set(fused) == {1, 2, 3, 4}


def test_fuse_tie_breaks_by_lower_id() -> None:
    # Identical single-list ranks → equal RRF scores → lower id first
    fused = RrfRankFusion(k=60).fuse([10], [20])
    assert fused == [10, 20]


def test_fuse_empty_lists() -> None:
    assert RrfRankFusion().fuse([], []) == []
    assert RrfRankFusion().fuse([1, 2], []) == [1, 2]


def test_fuse_single_list_preserves_order() -> None:
    assert RrfRankFusion().fuse([5, 3, 9]) == [5, 3, 9]
