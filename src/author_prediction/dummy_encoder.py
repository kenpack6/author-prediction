"""A dependency-free stand-in for step 2 (encoding), for testing pipeline
wiring before the real DeepStylometry-backed encoder is ready.

NOT a real style encoder. It hashes words into a fixed-size bag-of-words
vector, deterministically (via md5, not Python's randomized built-in
hash()), so tests are reproducible across runs and processes. Useful for
exercising the pipeline's control flow and interfaces -- not for real
authorship signal.
"""

from __future__ import annotations

import hashlib
from typing import Tuple

import numpy as np


def _stable_hash(s: str) -> int:
    """Deterministic string hash (Python's built-in hash() is randomized
    per-process by default, which would make tests flaky)."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


class HashingDummyEncoder:
    """Deterministic bag-of-words hashing encoder.

    Args:
        dim: Output vector dimensionality.
        seed: Mixed into the hash so different seeds produce unrelated
            (but each internally consistent) vector spaces -- useful for
            constructing test fixtures where "the same word" should NOT
            coincidentally collide across two unrelated encoder
            instances.
    """

    def __init__(self, dim: int = 32, seed: int = 0) -> None:
        self.dim = dim
        self.seed = seed

    def encode(self, text: str) -> Tuple[np.ndarray, int]:
        """Encode text into a hashed bag-of-words vector.

        Args:
            text: Span to encode.

        Returns:
            ``(vector, token_count)`` where ``token_count`` is a simple
            whitespace word count (not a real subword tokenizer count).
        """
        words = text.lower().split()
        vec = np.zeros(self.dim, dtype=np.float64)
        for word in words:
            idx = _stable_hash(f"{self.seed}:{word}") % self.dim
            vec[idx] += 1.0
        if not vec.any():
            vec[0] = 1.0  # avoid an all-zero vector for empty/whitespace input
        return vec, len(words)
