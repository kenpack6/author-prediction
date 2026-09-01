"""Summary statistics for a run_pipeline() result -- change points,
per-author breakdown, merge activity, similarity distribution.

Pure and dependency-free (beyond numpy): operates only on the plain
dicts run_pipeline() returns, so it's testable without a real encoder.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np


def _change_point_positions(author_ids: List[str]) -> List[int]:
    """Indices where the author differs from the immediately preceding one."""
    return [i for i in range(1, len(author_ids)) if author_ids[i] != author_ids[i - 1]]


def summarize_run(result: dict) -> dict:
    """Compute summary statistics for a run_pipeline() result.

    Args:
        result: The dict returned by
            ``pipeline_implementation.run_pipeline`` (must have
            ``assignments``, ``id_remap``, and ``profiles`` keys).

    Returns:
        Dict with:
          - ``num_sentences``: total spans processed.
          - ``num_raw_authors_before_merge``: distinct author ids that
            were ever registered during streaming, before merging.
          - ``num_final_authors``: distinct author ids remaining after
            merging (and smoothing, if applied).
          - ``merges_applied``: dict of ``{old_id: new_id}`` for every
            id that got folded into another (excludes ids that map to
            themselves).
          - ``num_change_points`` / ``change_point_positions``: where
            the assigned author differs from the previous sentence.
          - ``similarity_stats``: ``{"mean", "min", "max"}`` over all
            non-``None`` similarity scores (``None`` values, i.e. brand-
            new-author assignments, are excluded).
          - ``per_author``: list of dicts (sorted by first appearance)
            with ``author_id``, ``sample_count`` (from the tracker),
            ``sentences_assigned``, ``share_of_document``,
            ``first_seen``, ``last_seen``.
    """
    assignments = result["assignments"]
    profiles = result["profiles"]
    id_remap = result["id_remap"]

    num_sentences = len(assignments)
    final_author_ids = [a["author_id"] for a in assignments]

    merges_applied = {old: new for old, new in id_remap.items() if old != new}

    sims = [a["similarity"] for a in assignments if a["similarity"] is not None]
    similarity_stats: Dict[str, Optional[float]] = {
        "mean": float(np.mean(sims)) if sims else None,
        "min": float(np.min(sims)) if sims else None,
        "max": float(np.max(sims)) if sims else None,
    }

    first_seen: Dict[str, int] = {}
    for i, aid in enumerate(final_author_ids):
        first_seen.setdefault(aid, i)

    per_author = []
    for profile in profiles:
        aid = profile["author_id"]
        sentences_assigned = final_author_ids.count(aid)
        per_author.append(
            {
                "author_id": aid,
                "sample_count": profile["sample_count"],
                "sentences_assigned": sentences_assigned,
                "share_of_document": (
                    sentences_assigned / num_sentences if num_sentences else 0.0
                ),
                "first_seen": first_seen.get(aid),
                "last_seen": profile["last_seen"],
            }
        )
    per_author.sort(key=lambda a: a["first_seen"] if a["first_seen"] is not None else -1)

    return {
        "num_sentences": num_sentences,
        "num_raw_authors_before_merge": len(id_remap),
        "num_final_authors": len(set(final_author_ids)),
        "merges_applied": merges_applied,
        "num_change_points": len(_change_point_positions(final_author_ids)),
        "change_point_positions": _change_point_positions(final_author_ids),
        "similarity_stats": similarity_stats,
        "per_author": per_author,
    }


def format_run_summary(summary: dict) -> str:
    """Render a summarize_run() dict as a human-readable multi-line report.

    Args:
        summary: Output of :func:`summarize_run`.

    Returns:
        Formatted report string, ready to print.
    """
    lines = []
    lines.append(f"Processed {summary['num_sentences']} sentence(s)")
    lines.append(
        f"Authors before merge: {summary['num_raw_authors_before_merge']}  |  "
        f"after merge: {summary['num_final_authors']}"
    )

    if summary["merges_applied"]:
        lines.append("Merges applied:")
        for old_id, new_id in summary["merges_applied"].items():
            lines.append(f"  {old_id} -> {new_id}")
    else:
        lines.append("No merges were needed.")

    lines.append(
        f"Change points: {summary['num_change_points']} "
        f"at sentence indices {summary['change_point_positions']}"
    )

    sim = summary["similarity_stats"]
    if sim["mean"] is not None:
        lines.append(
            f"Similarity to matched author -- mean: {sim['mean']:.4f}, "
            f"min: {sim['min']:.4f}, max: {sim['max']:.4f}"
        )
    else:
        lines.append("No matched-author similarities recorded (every span was a new author).")

    lines.append("")
    lines.append("Per-author breakdown:")
    for author in summary["per_author"]:
        lines.append(
            f"  {author['author_id']}: {author['sentences_assigned']} sentence(s) "
            f"({author['share_of_document']:.1%} of doc), "
            f"first seen at {author['first_seen']}, last seen at {author['last_seen']}"
        )

    return "\n".join(lines)
