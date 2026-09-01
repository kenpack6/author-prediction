"""Pipeline step 3: cosine matching against a running set of author profiles.

This module is intentionally decoupled from segmentation/encoding (steps 1
and 2): it consumes already-encoded style vectors and has no dependency on
torch, transformers, or the segmenter. That keeps the handoff contract
simple across a team split along pipeline stages, and makes this class easy
to drop in behind an API boundary (vectors in as plain lists of floats,
JSON-serializable results out).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

ArrayLike = Union[np.ndarray, List[float]]


def _to_unit_vector(vector: ArrayLike) -> np.ndarray:
    """Convert to a float64 numpy array and L2-normalize it.

    Args:
        vector: Raw style vector (list or ndarray), any length.

    Returns:
        Unit-norm ``np.ndarray``.

    Raises:
        ValueError: If the vector is all-zero (cannot be normalized).
    """
    arr = np.asarray(vector, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero vector.")
    return arr / norm


@dataclass
class AuthorProfile:
    """Running style profile for one detected author.

    Attributes:
        author_id: Stable identifier, e.g. "Author_1".
        centroid: Unit-norm running-average (EMA) style vector.
        sample_count: Number of *accepted* (gated) updates folded into
            the centroid so far. The vector that created the profile
            counts as sample 1.
        last_seen: Position (sentence index / step counter) of the most
            recent update; used only if recency decay is enabled.
    """

    author_id: str
    centroid: np.ndarray
    sample_count: int = 1
    last_seen: int = 0


class AuthorProfileTracker:
    """Matches a stream of style vectors against running author profiles.

    This is pipeline step 3 ("Cosine Matching Against Active Author
    Frame") plus the EMA profile update that step implies. Call
    :meth:`step` once per sentence/window handed off by step 2.

    Args:
        sim_threshold: Cosine similarity (tau_match) at or above which a
            vector is assigned to the best-matching existing author
            rather than starting a new one. The reference implementation
            suggests calibrating this between 0.60 and 0.72 on labeled
            sample text for the mean-pooled DeepStylometry checkpoint.
        ema_alpha: Weight given to the *existing* centroid on each update
            (``1 - ema_alpha`` is the weight given to the new vector).
            Higher = profiles drift more slowly and resist noise more.
        min_tokens_for_update: Below this token count, a vector can still
            be *matched* against a profile, but won't be folded into
            (pollute) that profile's centroid. Guards against short,
            low-signal spans dragging a profile off course.
        recency_decay: Optional. If set, profiles not updated recently
            are penalized during matching: for a profile last updated
            ``d`` steps ago, the effective similarity is
            ``sim - recency_decay * d``. ``None`` disables this (matches
            the base algorithm with no decay).

    Raises:
        ValueError: If ``ema_alpha`` is outside ``[0, 1]``.
    """

    def __init__(
        self,
        sim_threshold: float = 0.65,
        ema_alpha: float = 0.90,
        min_tokens_for_update: int = 15,
        recency_decay: Optional[float] = None,
    ) -> None:
        if not (0.0 <= ema_alpha <= 1.0):
            raise ValueError("ema_alpha must be in [0, 1]")
        self.sim_threshold = sim_threshold
        self.ema_alpha = ema_alpha
        self.min_tokens_for_update = min_tokens_for_update
        self.recency_decay = recency_decay

        self.profiles: Dict[str, AuthorProfile] = {}
        self._next_id = 1
        self._step_count = 0

    def _new_author_id(self) -> str:
        author_id = f"Author_{self._next_id}"
        self._next_id += 1
        return author_id

    def match(self, vector: ArrayLike) -> Tuple[Optional[str], float]:
        """Find the best-matching existing author for a vector.

        Args:
            vector: Style vector to match (need not be pre-normalized).

        Returns:
            ``(author_id, similarity)`` for the best match, or
            ``(None, -1.0)`` if there are no profiles registered yet.
        """
        if not self.profiles:
            return None, -1.0

        unit_vec = _to_unit_vector(vector)
        best_id: Optional[str] = None
        best_sim = -math.inf

        for author_id, profile in self.profiles.items():
            sim = float(np.dot(profile.centroid, unit_vec))
            if self.recency_decay is not None:
                age = self._step_count - profile.last_seen
                sim -= self.recency_decay * age
            if sim > best_sim:
                best_sim = sim
                best_id = author_id

        return best_id, best_sim

    def step(
        self,
        vector: ArrayLike,
        token_count: int,
        position: Optional[int] = None,
    ) -> dict:
        """Process one vector: match, assign/register, and maybe update.

        The full step-3 decision plus the running-profile update in one
        call — invoke this once per sentence/window from whatever is
        orchestrating steps 1-4.

        Args:
            vector: Style vector for this sentence/window (from step 2).
            token_count: Token length of the underlying span; used only
                to gate profile updates (see ``min_tokens_for_update``).
            position: Optional external step index (e.g. sentence index
                in the document). Defaults to an internal
                auto-incrementing counter if omitted.

        Returns:
            JSON-serializable dict with ``author_id`` (str),
            ``similarity`` (float, to the assigned author; ``None`` for
            a brand-new author), ``is_new_author`` (bool), and
            ``profile_updated`` (bool, whether this call changed the
            centroid).
        """
        if position is None:
            position = self._step_count
        unit_vec = _to_unit_vector(vector)

        best_id, best_sim = self.match(unit_vec)
        is_new = best_id is None or best_sim < self.sim_threshold

        if is_new:
            author_id = self._new_author_id()
            self.profiles[author_id] = AuthorProfile(
                author_id=author_id,
                centroid=unit_vec,
                sample_count=1,
                last_seen=position,
            )
            result = {
                "author_id": author_id,
                "similarity": None,
                "is_new_author": True,
                "profile_updated": True,
            }
        else:
            author_id = best_id  # type: ignore[assignment]
            profile_updated = token_count >= self.min_tokens_for_update
            if profile_updated:
                self._update_profile(author_id, unit_vec, position)
            result = {
                "author_id": author_id,
                "similarity": best_sim,
                "is_new_author": False,
                "profile_updated": profile_updated,
            }

        self._step_count += 1
        return result

    def _update_profile(
        self, author_id: str, unit_vec: np.ndarray, position: int
    ) -> None:
        """Fold a new vector into an author's running centroid via EMA."""
        profile = self.profiles[author_id]
        blended = self.ema_alpha * profile.centroid + (1.0 - self.ema_alpha) * unit_vec
        norm = np.linalg.norm(blended)
        # Guard against the near-impossible case of exact cancellation.
        profile.centroid = blended / norm if norm > 0 else profile.centroid
        profile.sample_count += 1
        profile.last_seen = position

    def get_profile_summary(self) -> List[dict]:
        """Return a lightweight, JSON-serializable snapshot of all profiles.

        Deliberately omits raw centroid vectors -- for the API/interface
        layer to display current author state without shipping numpy
        arrays across the wire.

        Returns:
            List of dicts with ``author_id``, ``sample_count``, and
            ``last_seen`` per profile.
        """
        return [
            {
                "author_id": p.author_id,
                "sample_count": p.sample_count,
                "last_seen": p.last_seen,
            }
            for p in self.profiles.values()
        ]
