"""Run author diarization over a text file using the modular pipeline
(segmenter -> DeepStylometryEncoder -> AuthorProfileTracker -> merge),
and print a detailed run summary.

This replaces the old OnlineAuthorDiarizer-based script: sentence
splitting, encoding, matching, and merging are now separate, individually
testable pieces (segmenter.py, deep_stylometry_encoder.py,
profile_tracker.py, pipeline_implementation.py) tied together by
run_pipeline().

NOTE: DeepStylometryEncoder has not been run or verified in this
environment (no network access to Hugging Face, package not installed
here). Run this script yourself; see scripts/run_diarization_dummy.py
for a version that swaps in a dependency-free fake encoder if you want
to sanity-check the pipeline plumbing (segmentation, matching, merging,
reporting) independently of the real model.
"""

from author_prediction.deep_stylometry_encoder import DeepStylometryEncoder
from author_prediction.pipeline_implementation import run_pipeline
from author_prediction.profile_tracker import AuthorProfileTracker
from author_prediction.reporting import format_run_summary, summarize_run

DATA_PATH = "src/author_prediction/data/data_orth.txt"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    text = f.read()

tracker = AuthorProfileTracker(
    sim_threshold=0.96,
    ema_alpha=0.90,
    min_tokens_for_update=15,
)
encoder = DeepStylometryEncoder()

# Advance the sliding window by 1 sentence at a time by default. Increase
# ``stride`` to skip intermediate windows for a coarser scan over the text.
stride = 5

result = run_pipeline(
    text,
    encoder=encoder,
    tracker=tracker,
    context_window_size=20,
    stride=stride,
    merge_threshold=0.93,  # kept above sim_threshold -- see pipeline_implementation.py
)

summary = summarize_run(result)
print(format_run_summary(summary))

if result.get("merge_events"):
    print("\nAuthor merge events:")
    for event in result["merge_events"]:
        print(
            f"  - Merged {event['merged_from']} into {event['kept']} "
            f"(similarity={event['similarity']:.4f})"
        )

print("\nPer-sentence detail:")
assignments = result["assignments"]
for i, r in enumerate(assignments):
    changed = i > 0 and assignments[i]["author_id"] != assignments[i - 1]["author_id"]
    sim_str = f"{r['similarity']:.4f}" if r["similarity"] is not None else "  n/a "
    marker = "  <- author change" if changed else ""
    print(
        f"  [{i:>4}] {r['author_id']:<10} sim={sim_str} "
        f"new={str(r['is_new_author']):<5}{marker}"
    )
