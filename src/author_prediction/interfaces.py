"""Interfaces between pipeline stages.

These Protocols exist so each stage can be developed and tested in
isolation, on separate branches, without importing the others'
dependencies (torch, transformers, etc.). Anything that satisfies
EncoderProtocol's shape can plug into the pipeline as step 2 -- it
doesn't need to inherit from anything, just implement `encode`.

Pipeline stages and their owners (update as work is assigned):
    1. Segmentation & normalization  -> segmenter.py / io_utils.py
    2. Context-windowed encoding     -> (teammate) implements EncoderProtocol
    3. Cosine matching + profiles    -> profile_tracker.py
    4. Change-point smoothing        -> smoothing.py (stub for now)
"""

from __future__ import annotations

from typing import List, Protocol, Tuple

import numpy as np


class EncoderProtocol(Protocol):
    """Contract for step 2 (context-windowed encoding).

    Whoever builds the real DeepStylometry-backed encoder just needs a
    class with this method -- it does not need to import anything from
    this package, and this package does not need to import torch or
    transformers to type-check against it.
    """

    def encode(self, text: str) -> Tuple[np.ndarray, int]:
        """Encode a span of text into a style vector.

        Args:
            text: The span to encode (e.g. a sliding-window join of a
                few sentences, per step 2's design).

        Returns:
            ``(vector, token_count)`` -- the style embedding (any
            length; ``AuthorProfileTracker`` normalizes it) and the
            number of tokens the span consumed, used by step 3 to gate
            profile updates.
        """
        ...


class SmootherProtocol(Protocol):
    """Contract for step 4 (change-point smoothing / segment
    reconciliation).

    Takes the raw, greedy per-step assignments from step 3 and returns
    a cleaned-up sequence -- e.g. suppressing single-step flip-flops
    where one noisy vector briefly overrides an otherwise-stable run of
    the same author.
    """

    def smooth(self, assignments: List[dict]) -> List[dict]:
        """Post-process a sequence of step-3 results.

        Args:
            assignments: The list of dicts returned by repeated calls
                to ``AuthorProfileTracker.step()``, in order.

        Returns:
            A same-length list of dicts in the same shape, with
            ``author_id`` values potentially revised.
        """
        ...
