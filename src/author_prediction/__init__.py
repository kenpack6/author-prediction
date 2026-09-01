"""author_prediction: verse-style text segmentation for authorship modeling."""

import argparse
from pathlib import Path

from author_prediction.io_utils import (
    iter_input_files,
    segment_file,
    write_csv,
    write_jsonl,
)


def main() -> None:
    """CLI entry point: segment raw text file(s) into verse-like chunks."""
    parser = argparse.ArgumentParser(
        prog="author-prediction",
        description=(
            "Split raw text files into verse-like segments (grouped by "
            "sentence count) for feeding into a downstream authorship "
            "model."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A .txt file, or a directory of .txt files (searched recursively).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("segments.jsonl"),
        help="Output path. Format is inferred from the extension (.jsonl or .csv). Default: segments.jsonl",
    )
    parser.add_argument(
        "-n",
        "--sentences-per-segment",
        type=int,
        default=3,
        help="Number of sentences to group into each segment. Default: 3",
    )
    parser.add_argument(
        "--tokenizer",
        type=str,
        default=None,
        help=(
            "Optional HuggingFace tokenizer name (e.g. answerdotai/ModernBERT-base) "
            "used to additionally cap segments by token count. Requires the "
            "'transformers' extra: pip install 'author-prediction[token-budget]'"
        ),
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max tokens per segment. Only applied if --tokenizer is set.",
    )
    args = parser.parse_args()

    tokenizer = None
    if args.tokenizer is not None:
        try:
            from transformers import AutoTokenizer
        except ImportError as e:
            raise SystemExit(
                "--tokenizer requires the 'transformers' package. Install with: "
                "pip install 'author-prediction[token-budget]'"
            ) from e
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

    files = iter_input_files(args.input)
    print(f"Found {len(files)} file(s) to segment.")

    all_records = []
    for path in files:
        records = segment_file(
            path,
            sentences_per_segment=args.sentences_per_segment,
            tokenizer=tokenizer,
            max_tokens=args.max_tokens,
        )
        print(f"  {path}: {len(records)} segment(s)")
        all_records.extend(records)

    suffix = args.output.suffix.lower()
    if suffix == ".csv":
        n = write_csv(all_records, args.output)
    else:
        n = write_jsonl(all_records, args.output)

    print(f"Wrote {n} segment(s) to {args.output}")
