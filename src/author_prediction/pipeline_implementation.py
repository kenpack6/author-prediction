"""Main pipeline orchestrator: ties steps 1-4 together end to end.

    1. Segmentation & normalization  -> segmenter.split_into_sentences
    2. Context-windowed encoding     -> injected EncoderProtocol
    3. Cosine matching + profiles    -> AuthorProfileTracker
    3b. Profile merge consolidation  -> merge_similar_profiles (this file)
    4. Change-point smoothing        -> injected SmootherProtocol

Two similarity thresholds are used here, deliberately kept separate:

  - tracker.sim_threshold (tau_match): decided ONLINE, per incoming
    vector, against noisy single-sample evidence. Kept conservative so a
    weak/ambiguous span doesn't get force-matched to the wrong author.
  - merge_threshold (tau_merge), used by merge_similar_profiles below:
    decided OFFLINE, after processing, by comparing two SETTLED
    centroids (each already averaged over potentially many samples)
    against each other. This repairs over-fragmentation -- cases where
    the same writer got split into multiple profiles early on (e.g. a
    weak first sentence, or genuinely varying content) but their
    centroids converged to the same direction once enough evidence
    accumulated.

Because merge_threshold compares two already-averaged, more reliable
vectors rather than one noisy sample against a settled one, it is
typically set >= tau_match -- merging is a bigger, harder-to-undo
decision than a single assignment, so it should demand more confidence,
not less. Tune the two independently against your own data.

Note merge_similar_profiles uses AVERAGE-linkage chaining (each merge
produces a new blended centroid, and subsequent comparisons are against
that blend), not single-linkage (comparing against the original member
vectors). This is the more conservative of the two: a chain of merges
only continues if the *blended* centroid stays close enough to the next
candidate, so it's less prone to chaining together profiles that only
resemble each other through a distant intermediate.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from author_prediction.interfaces import EncoderProtocol, SmootherProtocol
from author_prediction.profile_tracker import AuthorProfileTracker
from author_prediction.segmenter import split_into_sentences


def _author_number(author_id: str) -> int:
    """Extract the integer suffix from an 'Author_N' id, for tie-breaking."""
    return int(author_id.rsplit("_", 1)[-1])


def merge_similar_profiles(
    tracker: AuthorProfileTracker,
    merge_threshold: float,
) -> Dict[str, str]:
    """Consolidate author profiles whose centroids converged to a similar
    direction, post-hoc.

    Repeatedly merges the most-similar pair of profiles whose cosine
    similarity is at or above ``merge_threshold``, until no remaining
    pair qualifies. Merged centroids are combined as a sample-count-
    weighted average and re-normalized -- NOT an EMA, since both sides
    are treated as equally "settled" evidence here, weighted by how much
    data produced each one. The profile with more accumulated samples
    survives (ties broken by lower author id); the other is removed.

    Note this uses average-linkage-style chaining: each merge produces a
    new blended centroid, and later comparisons are made against that
    blend, not the original member vectors. So A and C can end up
    merged (via an intermediate B) even if they weren't directly close
    enough to begin with -- but only if the blended A+B centroid is
    itself still close enough to C. That's more conservative than
    single-linkage chaining and usually what you want for repairing
    fragmentation without over-merging.

    Mutates ``tracker.profiles`` in place.

    Args:
        tracker: The tracker whose profiles should be consolidated.
            Typically called once, after a full document/stream has
            been processed with repeated ``tracker.step()`` calls.
        merge_threshold: Cosine similarity (tau_merge) at or above which
            two profiles are considered the same underlying author.

    Returns:
        id_remap: mapping from every original author_id (as it existed
        before this call) to the author_id it ends up under after
        merging. Surviving authors map to themselves. Use
        :func:`apply_id_remap` to relabel already-collected ``step()``
        results with this.
    """
    id_remap: Dict[str, str] = {aid: aid for aid in tracker.profiles}

    while len(tracker.profiles) >= 2:
        ids = list(tracker.profiles.keys())
        best_pair = None
        best_sim = -math.inf

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a = tracker.profiles[ids[i]]
                b = tracker.profiles[ids[j]]
                sim = float(np.dot(a.centroid, b.centroid))
                if sim > best_sim:
                    best_sim = sim
                    best_pair = (ids[i], ids[j])

        if best_sim < merge_threshold:
            break  # nothing left worth merging

        id_a, id_b = best_pair
        profile_a = tracker.profiles[id_a]
        profile_b = tracker.profiles[id_b]

        # Higher sample_count survives (more reliable estimate); ties
        # broken by lower numeric author id, for determinism.
        if (profile_a.sample_count, -_author_number(id_a)) >= (
            profile_b.sample_count,
            -_author_number(id_b),
        ):
            keep_id, drop_id = id_a, id_b
        else:
            keep_id, drop_id = id_b, id_a

        keep = tracker.profiles[keep_id]
        drop = tracker.profiles[drop_id]

        total = keep.sample_count + drop.sample_count
        blended = (
            keep.sample_count * keep.centroid + drop.sample_count * drop.centroid
        ) / total
        norm = np.linalg.norm(blended)
        keep.centroid = blended / norm if norm > 0 else keep.centroid
        keep.sample_count = total
        keep.last_seen = max(keep.last_seen, drop.last_seen)

        del tracker.profiles[drop_id]

        for original_id, current_target in id_remap.items():
            if current_target == drop_id:
                id_remap[original_id] = keep_id

    return id_remap


def apply_id_remap(assignments: List[dict], id_remap: Dict[str, str]) -> List[dict]:
    """Relabel a list of ``step()`` results after ``merge_similar_profiles``.

    Args:
        assignments: Results previously returned by
            ``AuthorProfileTracker.step()``.
        id_remap: Mapping returned by ``merge_similar_profiles``.

    Returns:
        A new list of dicts with ``author_id`` values updated to their
        post-merge canonical id. The input list is not mutated.
    """
    relabeled = []
    for record in assignments:
        new_record = dict(record)
        new_record["author_id"] = id_remap.get(record["author_id"], record["author_id"])
        relabeled.append(new_record)
    return relabeled


def run_pipeline(
    text: str,
    encoder: EncoderProtocol,
    tracker: AuthorProfileTracker,
    context_window_size: int = 3,
    stride: int = 1,
    merge_threshold: Optional[float] = 0.85,
    smoother: Optional[SmootherProtocol] = None,
) -> dict:
    """Run the full pipeline over one document: segment, encode, match,
    merge, and (optionally) smooth.

    Args:
        text: Raw document text (step 1 input).
        encoder: Object satisfying ``EncoderProtocol`` (step 2).
        tracker: An ``AuthorProfileTracker`` instance (step 3). Can be
            reused/shared across multiple ``run_pipeline`` calls if you
            want author profiles to persist across a whole corpus
            rather than resetting per document.
        context_window_size: Number of trailing sentences joined into
            each encoded span (mirrors the sliding-window design).
        stride: Number of sentence positions to advance between encoded
            windows. ``1`` keeps the original behavior of stepping one
            sentence at a time; larger values skip over intermediate
            segments.
        merge_threshold: tau_merge for post-hoc profile consolidation.
            Pass ``None`` (or >= 1.0) to disable merging entirely.
        smoother: Optional object satisfying ``SmootherProtocol``
            (step 4). If omitted, raw per-step assignments are returned
            unsmoothed -- step 4 isn't built yet, this is just the seam
            for it.

    Returns:
        Dict with:
          - ``"assignments"``: list of result dicts for each processed
            window (``author_id``, ``similarity``, ``is_new_author``,
            ``profile_updated``), post-merge and post-smoothing.
          - ``"id_remap"``: the merge remapping applied, for auditing.
          - ``"profiles"``: ``tracker.get_profile_summary()`` after
            merging.
    """
    if stride <= 0:
        raise ValueError("stride must be a positive integer")

    sentences = split_into_sentences(text)
    assignments: List[dict] = []

    for i in range(0, len(sentences), stride):
        start = max(0, i - context_window_size + 1)
        window_text = " ".join(sentences[start : i + 1])
        vector, token_count = encoder.encode(window_text)
        result = tracker.step(vector, token_count, position=i)
        assignments.append(result)

    id_remap: Dict[str, str] = {aid: aid for aid in tracker.profiles}
    if merge_threshold is not None and merge_threshold < 1.0:
        id_remap = merge_similar_profiles(tracker, merge_threshold)
        assignments = apply_id_remap(assignments, id_remap)

    if smoother is not None:
        assignments = smoother.smooth(assignments)

    return {
        "assignments": assignments,
        "id_remap": id_remap,
        "profiles": tracker.get_profile_summary(),
    }
