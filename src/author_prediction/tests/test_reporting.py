import numpy as np
import pytest

from author_prediction.dummy_encoder import HashingDummyEncoder
from author_prediction.pipeline_implementation import (
    apply_id_remap,
    merge_similar_profiles,
    run_pipeline,
)
from author_prediction.profile_tracker import AuthorProfile, AuthorProfileTracker
from author_prediction.smoothing import NoOpSmoother


def make_tracker_with_profiles(profiles: dict) -> AuthorProfileTracker:
    """Build a tracker with hand-crafted profiles, bypassing step()."""
    tracker = AuthorProfileTracker()
    tracker.profiles = profiles
    return tracker


def unit(v):
    arr = np.asarray(v, dtype=np.float64)
    return arr / np.linalg.norm(arr)


class TestMergeSimilarProfiles:
    def test_merges_pair_above_threshold(self):
        profiles = {
            "Author_1": AuthorProfile("Author_1", unit([1.0, 0.0]), sample_count=5),
            "Author_2": AuthorProfile("Author_2", unit([0.99, 0.01]), sample_count=3),
        }
        tracker = make_tracker_with_profiles(profiles)

        id_remap = merge_similar_profiles(tracker, merge_threshold=0.9)

        assert len(tracker.profiles) == 1
        assert "Author_1" in tracker.profiles
        assert id_remap == {"Author_1": "Author_1", "Author_2": "Author_1"}

    def test_higher_sample_count_survives(self):
        profiles = {
            "Author_1": AuthorProfile("Author_1", unit([1.0, 0.0]), sample_count=2),
            "Author_2": AuthorProfile("Author_2", unit([0.99, 0.01]), sample_count=20),
        }
        tracker = make_tracker_with_profiles(profiles)

        id_remap = merge_similar_profiles(tracker, merge_threshold=0.9)

        assert "Author_2" in tracker.profiles
        assert "Author_1" not in tracker.profiles
        assert id_remap["Author_1"] == "Author_2"
        assert tracker.profiles["Author_2"].sample_count == 22

    def test_no_merge_below_threshold(self):
        profiles = {
            "Author_1": AuthorProfile("Author_1", unit([1.0, 0.0]), sample_count=5),
            "Author_2": AuthorProfile("Author_2", unit([0.0, 1.0]), sample_count=5),
        }
        tracker = make_tracker_with_profiles(profiles)

        id_remap = merge_similar_profiles(tracker, merge_threshold=0.9)

        assert len(tracker.profiles) == 2
        assert id_remap == {"Author_1": "Author_1", "Author_2": "Author_2"}

    def test_merged_centroid_is_unit_norm(self):
        profiles = {
            "Author_1": AuthorProfile("Author_1", unit([1.0, 0.0]), sample_count=1),
            "Author_2": AuthorProfile("Author_2", unit([0.9, 0.4]), sample_count=1),
        }
        tracker = make_tracker_with_profiles(profiles)

        merge_similar_profiles(tracker, merge_threshold=0.5)

        surviving = next(iter(tracker.profiles.values()))
        assert np.isclose(np.linalg.norm(surviving.centroid), 1.0)

    def test_average_linkage_chain_merge(self):
        # Four profiles at 0, 15, 30, 45 degrees apart. Adjacent pairs are
        # close (cos15 ~= 0.966); the endpoints alone are not (cos45 ~=
        # 0.707), well below the threshold used here. Average-linkage
        # chaining should still collapse all four into one via the
        # intermediate blended centroids.
        import math

        def deg(angle_deg):
            r = math.radians(angle_deg)
            return np.array([math.cos(r), math.sin(r)])

        a, b, c, d = deg(0), deg(15), deg(30), deg(45)
        assert np.dot(a, d) < 0.85  # endpoints are NOT directly similar enough

        profiles = {
            "Author_1": AuthorProfile("Author_1", a, sample_count=1),
            "Author_2": AuthorProfile("Author_2", b, sample_count=1),
            "Author_3": AuthorProfile("Author_3", c, sample_count=1),
            "Author_4": AuthorProfile("Author_4", d, sample_count=1),
        }
        tracker = make_tracker_with_profiles(profiles)

        merge_similar_profiles(tracker, merge_threshold=0.85)

        assert len(tracker.profiles) == 1

    def test_single_profile_is_a_noop(self):
        profiles = {"Author_1": AuthorProfile("Author_1", unit([1.0, 0.0]), sample_count=5)}
        tracker = make_tracker_with_profiles(profiles)

        id_remap = merge_similar_profiles(tracker, merge_threshold=0.5)

        assert len(tracker.profiles) == 1
        assert id_remap == {"Author_1": "Author_1"}


class TestApplyIdRemap:
    def test_relabels_matching_ids(self):
        assignments = [
            {"author_id": "Author_2", "similarity": 0.7},
            {"author_id": "Author_1", "similarity": 0.8},
        ]
        remap = {"Author_1": "Author_1", "Author_2": "Author_1"}

        relabeled = apply_id_remap(assignments, remap)

        assert [r["author_id"] for r in relabeled] == ["Author_1", "Author_1"]

    def test_does_not_mutate_input(self):
        assignments = [{"author_id": "Author_2"}]
        apply_id_remap(assignments, {"Author_2": "Author_1"})
        assert assignments[0]["author_id"] == "Author_2"

    def test_unmapped_id_passes_through(self):
        assignments = [{"author_id": "Author_9"}]
        relabeled = apply_id_remap(assignments, {"Author_1": "Author_1"})
        assert relabeled[0]["author_id"] == "Author_9"


class TestRunPipeline:
    def test_returns_expected_shape(self):
        text = "This is one sentence. This is another sentence. And a third one."
        tracker = AuthorProfileTracker(sim_threshold=0.3, ema_alpha=0.8)
        encoder = HashingDummyEncoder(dim=16, seed=0)

        result = run_pipeline(text, encoder, tracker, context_window_size=2)

        assert set(result.keys()) == {"assignments", "id_remap", "profiles"}
        assert len(result["assignments"]) == 3
        for record in result["assignments"]:
            assert "author_id" in record

    def test_disabling_merge_leaves_profiles_untouched(self):
        text = "Sentence one here. Sentence two here. Sentence three here."
        tracker = AuthorProfileTracker(sim_threshold=0.99, ema_alpha=0.8)
        encoder = HashingDummyEncoder(dim=16, seed=0)

        result = run_pipeline(text, encoder, tracker, merge_threshold=None)

        # With an (almost) impossible match threshold, every sentence
        # should register as its own author, and merging is disabled.
        assert result["id_remap"] == {
            aid: aid for aid in {r["author_id"] for r in result["assignments"]}
        }

    def test_smoother_is_applied_when_provided(self):
        text = "One sentence. Two sentence. Three sentence."
        tracker = AuthorProfileTracker(sim_threshold=0.3, ema_alpha=0.8)
        encoder = HashingDummyEncoder(dim=16, seed=0)

        result = run_pipeline(text, encoder, tracker, smoother=NoOpSmoother())

        assert len(result["assignments"]) == 3

    def test_empty_text_returns_empty_assignments(self):
        tracker = AuthorProfileTracker()
        encoder = HashingDummyEncoder(dim=16, seed=0)

        result = run_pipeline("", encoder, tracker)

        assert result["assignments"] == []
