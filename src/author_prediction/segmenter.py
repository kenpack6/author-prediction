"""Split raw scriptural text into verse-like segments.

The source files have no explicit verse markers, so segments are built by
detecting sentence boundaries and grouping a fixed number of sentences
together (optionally capped by a token budget so segments stay small enough
for a downstream model, e.g. DeepStylometry's ModernBERT-based encoder).

This is a lightweight, dependency-free sentence splitter tuned for
formal/archaic English prose (the register scripture is usually written
in). It is not a full NLP sentence tokenizer: it uses punctuation +
capitalization heuristics and a small abbreviation list. For messier or
multilingual text, swap ``split_into_sentences`` for a proper library
(spaCy, pysbd, nltk's punkt) without changing ``group_sentences`` or
``segment_text``.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Protocol

# Common abbreviations that end in a period but should NOT be treated as a
# sentence boundary. Lowercased, including the trailing period.
_ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.", "vs.",
    "etc.", "e.g.", "i.e.", "ca.", "cf.", "al.", "no.", "vol.", "ch.",
    "fig.", "rev.",
}

# A candidate sentence boundary: one or more end-punctuation marks
# (optionally followed by a closing quote/paren), then whitespace, then
# the start of what looks like a new sentence (capital letter, digit, or
# an opening quote/paren).
_BOUNDARY_RE = re.compile(r"([.!?]+[\'\"\)\]]*)\s+(?=[A-Z0-9\"'(\[])")


class _Tokenizer(Protocol):
    """Minimal protocol matching a HuggingFace tokenizer's __call__."""

    def __call__(self, text: str, add_special_tokens: bool = ...) -> Any: ...


def split_into_sentences(text: str) -> List[str]:
    """Split a block of text into sentences.

    Uses punctuation + capitalization heuristics; treats known
    abbreviations and short all-caps/initial-like tokens (e.g. "J.") as
    non-boundaries so it doesn't split on things like "J. R. R. Tolkien"
    or "St. Paul".

    Args:
        text: Raw input text (may span multiple paragraphs/lines).

    Returns:
        List of sentence strings, whitespace-normalized. Empty list if
        ``text`` is empty or whitespace-only.
    """
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []

    sentences: List[str] = []
    start = 0
    for match in _BOUNDARY_RE.finditer(normalized):
        end = match.end(1)
        candidate = normalized[start:end].strip()
        if not candidate:
            continue

        last_token = candidate.rstrip("'\")]").split(" ")[-1] if candidate else ""
        last_token_lower = last_token.lower()

        is_abbreviation = last_token_lower in _ABBREVIATIONS
        # Single capital letter + period, e.g. "J." in an initial.
        is_initial = len(last_token) == 2 and last_token[0].isupper() and last_token[1] == "."

        if is_abbreviation or is_initial:
            continue

        sentences.append(candidate)
        start = match.end()

    tail = normalized[start:].strip()
    if tail:
        sentences.append(tail)

    return sentences


def group_sentences(
    sentences: List[str],
    sentences_per_segment: int = 3,
    tokenizer: Optional[_Tokenizer] = None,
    max_tokens: Optional[int] = None,
) -> List[str]:
    """Group sentences into segments.

    A new segment starts once the current one reaches
    ``sentences_per_segment`` sentences, OR (if ``tokenizer`` and
    ``max_tokens`` are given) once adding the next sentence would push the
    segment's token count to or past ``max_tokens`` -- whichever comes
    first. A segment is never empty: if a single sentence alone exceeds
    ``max_tokens``, it still becomes its own segment rather than being
    split mid-sentence.

    Args:
        sentences: Sentences to group, in order.
        sentences_per_segment: Max sentences per segment. Must be >= 1.
        tokenizer: Optional HuggingFace-style tokenizer used to enforce
            ``max_tokens``. If omitted, only ``sentences_per_segment``
            applies.
        max_tokens: Optional token budget per segment. Ignored if
            ``tokenizer`` is not provided.

    Returns:
        List of segment strings (sentences joined with a single space).

    Raises:
        ValueError: If ``sentences_per_segment`` < 1.
    """
    if sentences_per_segment < 1:
        raise ValueError("sentences_per_segment must be >= 1")

    def token_len(s: str) -> int:
        if tokenizer is None:
            return 0
        return len(tokenizer(s, add_special_tokens=False)["input_ids"])

    segments: List[str] = []
    current: List[str] = []

    for sentence in sentences:
        would_be = current + [sentence]
        over_sentence_cap = len(would_be) > sentences_per_segment
        over_token_cap = (
            tokenizer is not None
            and max_tokens is not None
            and current  # never flush an empty segment because of one long sentence
            and token_len(" ".join(would_be)) > max_tokens
        )

        if current and (over_sentence_cap or over_token_cap):
            segments.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)

    if current:
        segments.append(" ".join(current))

    return segments


def segment_text(
    text: str,
    sentences_per_segment: int = 3,
    tokenizer: Optional[_Tokenizer] = None,
    max_tokens: Optional[int] = None,
) -> List[str]:
    """Split raw text directly into verse-like segments.

    Convenience wrapper combining :func:`split_into_sentences` and
    :func:`group_sentences`.

    Args:
        text: Raw input text.
        sentences_per_segment: Max sentences per segment.
        tokenizer: Optional tokenizer to enforce a token budget.
        max_tokens: Optional per-segment token budget.

    Returns:
        List of segment strings. Empty list if ``text`` has no sentences.
    """
    sentences = split_into_sentences(text)
    return group_sentences(
        sentences,
        sentences_per_segment=sentences_per_segment,
        tokenizer=tokenizer,
        max_tokens=max_tokens,
    )
