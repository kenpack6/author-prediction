import numpy as np
import pytest

from author_prediction.profile_tracker import AuthorProfileTracker, _to_unit_vector


def unit(v):
    return _to_unit_vector(v)


class TestToUnitVector:
    def test_normalizes(self):
        v = _to_unit_vector([3.0, 4.0])
        assert np.isclose(np.linalg.norm(v), 1.0)

    def test_zero_vector_raises(self):
        with pytest.raises(ValueError):
            _to_unit_vector([0.0, 0.0, 0.0])


class TestFirstVectorCreatesAuthor:
    def test_empty_tracker_registers_author_1(self):
        tracker = AuthorProfileTracker()
        result = tracker.step([1.0, 0.0], token_count=50)
        assert result["author_id"] == "Author_1"
        assert result["is_new_author"] is True
        assert result["similarity"] is None
        assert tracker.profiles["Author_1"].sample_count == 1


class TestMatchingAndAssignment:
    def test_similar_vector_matches_existing_author(self):
        tracker = AuthorProfileTracker(sim_threshold=0.9)
        tracker.step([1.0, 0.0], token_count=50)
        # Nearly identical direction -> should match Author_1.
        result = tracker.step([0.99, 0.01], token_count=50)
        assert result["author_id"] == "Author_1"
        assert result["is_new_author"] is False
        assert result["similarity"] > 0.9

    def test_dissimilar_vector_creates_new_author(self):
        tracker = AuthorProfileTracker(sim_threshold=0.9)
        tracker.step([1.0, 0.0], token_count=50)
        # Orthogonal direction -> similarity ~0, well below threshold.
        result = tracker.step([0.0, 1.0], token_count=50)
        assert result["author_id"] == "Author_2"
        assert result["is_new_author"] is True
        assert len(tracker.profiles) == 2

    def test_match_picks_highest_similarity_among_multiple_profiles(self):
        tracker = AuthorProfileTracker(sim_threshold=0.9)
        tracker.step([1.0, 0.0, 0.0], token_count=50)  # Author_1
        tracker.step([0.0, 1.0, 0.0], token_count=50)  # Author_2 (orthogonal)
        best_id, sim = tracker.match([0.95, 0.05, 0.0])
        assert best_id == "Author_1"
        assert sim > 0.9


class TestEmaUpdate:
    def test_update_moves_centroid_toward_new_vector(self):
        tracker = AuthorProfileTracker(sim_threshold=0.5, ema_alpha=0.5)
        tracker.step([1.0, 0.0], token_count=50)
        before = tracker.profiles["Author_1"].centroid.copy()
        tracker.step([0.0, 1.0], token_count=50)  # still matches at alpha=0.5? check below
        # With sim_threshold=0.5 and orthogonal vectors (sim=0), this actually
        # registers a NEW author, not an update -- demonstrates the gate.
        assert "Author_2" in tracker.profiles
        assert np.array_equal(tracker.profiles["Author_1"].centroid, before)

    def test_update_actually_blends_and_renormalizes(self):
        tracker = AuthorProfileTracker(sim_threshold=0.5, ema_alpha=0.8)
        tracker.step([1.0, 0.0], token_count=50)
        # A vector close enough to match (sim ~0.71 > 0.5) but different
        # enough to visibly shift the centroid.
        tracker.step([0.7, 0.7], token_count=50)
        centroid = tracker.profiles["Author_1"].centroid
        assert np.isclose(np.linalg.norm(centroid), 1.0)
        # Centroid should have moved off the original [1, 0] direction.
        assert centroid[1] > 0.0

    def test_sample_count_increments_on_update(self):
        tracker = AuthorProfileTracker(sim_threshold=0.5, ema_alpha=0.8)
        tracker.step([1.0, 0.0], token_count=50)
        tracker.step([0.9, 0.1], token_count=50)
        assert tracker.profiles["Author_1"].sample_count == 2


class TestMinTokensGate:
    def test_short_span_matches_but_does_not_update_profile(self):
        tracker = AuthorProfileTracker(
            sim_threshold=0.5, ema_alpha=0.8, min_tokens_for_update=15
        )
        tracker.step([1.0, 0.0], token_count=50)
        before = tracker.profiles["Author_1"].centroid.copy()
        result = tracker.step([0.9, 0.1], token_count=5)  # below the gate
        assert result["author_id"] == "Author_1"
        assert result["profile_updated"] is False
        assert np.array_equal(tracker.profiles["Author_1"].centroid, before)
        assert tracker.profiles["Author_1"].sample_count == 1  # unchanged


class TestRecencyDecay:
    def test_stale_profile_penalized_enough_to_lose_match(self):
        # Two authors; Author_1 goes stale while Author_2 keeps getting
        # updated, advancing the internal step counter.
        tracker = AuthorProfileTracker(
            sim_threshold=0.8, ema_alpha=0.9, recency_decay=0.05
        )
        tracker.step([1.0, 0.0], token_count=50)  # Author_1, position 0
        tracker.step([0.0, 1.0], token_count=50)  # Author_2, position 1 (orthogonal)
        for _ in range(10):
            tracker.step([0.0, 1.0], token_count=50)  # keep Author_2 fresh

        # A vector close to Author_1's original direction, but Author_1 is
        # now 11 steps stale -> decay penalty should push it below threshold.
        result = tracker.step([0.99, 0.01], token_count=50)
        assert result["is_new_author"] is True

    def test_no_decay_by_default(self):
        tracker = AuthorProfileTracker(sim_threshold=0.8, ema_alpha=0.9)
        tracker.step([1.0, 0.0], token_count=50)
        tracker.step([0.0, 1.0], token_count=50)
        for _ in range(50):
            tracker.step([0.0, 1.0], token_count=50)
        # Without recency_decay, staleness shouldn't matter.
        result = tracker.step([0.99, 0.01], token_count=50)
        assert result["author_id"] == "Author_1"
        assert result["is_new_author"] is False


class TestProfileSummary:
    def test_summary_is_json_safe(self):
        import json

        tracker = AuthorProfileTracker(sim_threshold=0.9)
        tracker.step([1.0, 0.0], token_count=50)
        tracker.step([0.0, 1.0], token_count=50)
        summary = tracker.get_profile_summary()
        json.dumps(summary)  # raises if not JSON-serializable
        assert {p["author_id"] for p in summary} == {"Author_1", "Author_2"}


class TestInvalidConfig:
    def test_ema_alpha_out_of_range_raises(self):
        with pytest.raises(ValueError):
            AuthorProfileTracker(ema_alpha=1.5)
        with pytest.raises(ValueError):
            AuthorProfileTracker(ema_alpha=-0.1)
