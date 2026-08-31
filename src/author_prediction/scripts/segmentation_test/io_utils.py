"""File I/O helpers for the segmenter: reading raw text and writing output."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from author_prediction.segmenter import segment_text, _Tokenizer


def iter_input_files(path: Path) -> List[Path]:
    """Resolve an input path to a list of ``.txt`` files.

    Args:
        path: A single ``.txt`` file, or a directory containing ``.txt``
            files (searched recursively).

    Returns:
        Sorted list of file paths.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If ``path`` is a file but not ``.txt``, or a
            directory with no ``.txt`` files.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Expected a .txt file, got: {path}")
        return [path]

    files = sorted(path.rglob("*.txt"))
    if not files:
        raise ValueError(f"No .txt files found under directory: {path}")
    return files


def segment_file(
    path: Path,
    sentences_per_segment: int = 3,
    tokenizer: Optional[_Tokenizer] = None,
    max_tokens: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Read a single text file and segment its contents.

    Args:
        path: Path to a ``.txt`` file.
        sentences_per_segment: Max sentences per segment.
        tokenizer: Optional tokenizer to enforce a token budget.
        max_tokens: Optional per-segment token budget.

    Returns:
        List of records, one per segment, each with ``source_file``,
        ``segment_index``, and ``text``.
    """
    text = path.read_text(encoding="utf-8")
    segments = segment_text(
        text,
        sentences_per_segment=sentences_per_segment,
        tokenizer=tokenizer,
        max_tokens=max_tokens,
    )
    return [
        {
            "source_file": str(path),
            "segment_index": i,
            "text": segment,
        }
        for i, segment in enumerate(segments)
    ]


def write_jsonl(records: Iterable[Dict[str, Any]], out_path: Path) -> int:
    """Write records to a JSON Lines file, one JSON object per line.

    Args:
        records: Records to write.
        out_path: Destination path. Parent directories are created if
            needed.

    Returns:
        Number of records written.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_csv(records: List[Dict[str, Any]], out_path: Path) -> int:
    """Write records to a CSV file.

    Args:
        records: Records to write. All records must share the same keys
            (as produced by :func:`segment_file`).
        out_path: Destination path. Parent directories are created if
            needed.

    Returns:
        Number of records written.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        out_path.write_text("", encoding="utf-8")
        return 0

    fieldnames = list(records[0].keys())
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return len(records)
