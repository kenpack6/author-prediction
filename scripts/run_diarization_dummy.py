"""Same as run_diarization.py, but with HashingDummyEncoder instead of
the real DeepStylometry model. Use this to sanity-check the pipeline
plumbing -- segmentation, matching, merging, and reporting -- without
needing network access or the deep_stylometry package installed.

The similarity scores and author assignments here are NOT meaningful
style signal (HashingDummyEncoder is a bag-of-words hash, not a
stylometric encoder) -- this only proves the wiring works end to end.
"""

from author_prediction.dummy_encoder import HashingDummyEncoder
from author_prediction.pipeline_implementation import run_pipeline
from author_prediction.profile_tracker import AuthorProfileTracker
from author_prediction.reporting import format_run_summary, summarize_run
from author_prediction.segmenter import split_into_sentences

DATA_PATH = "src/author_prediction/data/data_orth.txt"
MAX_CHARS: int | None = 30000
MAX_SENTENCES: int | None = 100


def load_limited_text(path: str, max_chars: int | None = None, max_sentences: int | None = None) -> str:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if max_chars is not None and max_chars > 0:
        text = text[:max_chars]
    if max_sentences is not None and max_sentences > 0:
        sentences = split_into_sentences(text)
        text = " ".join(sentences[:max_sentences])
    return text


def print_progress(progress: float, processed: int, total: int) -> None:
    pct = int(progress * 100)
    print(f"Processing text: {pct}% ({processed}/{total} sentences)", end="\r")


text = load_limited_text(DATA_PATH, max_chars=MAX_CHARS, max_sentences=MAX_SENTENCES)

tracker = AuthorProfileTracker(
    sim_threshold=0.30,  # much lower than the real-model default -- hashed
                         # bag-of-words vectors don't separate the way real
                         # style embeddings do, so 0.90 would never match here
    ema_alpha=0.90,
    min_tokens_for_update=15,
)
encoder = HashingDummyEncoder(dim=64, seed=0)

# Use a larger stride to skip intermediate windows in the dummy run;
# stride=1 is the original behavior, stride=2/3/5 gives a coarser scan.
stride = 2

result = run_pipeline(
    text,
    encoder=encoder,
    tracker=tracker,
    context_window_size=20,
    stride=stride,
    merge_threshold=0.5,
    progress_callback=print_progress,
)

print("\n")

summary = summarize_run(result)
print(format_run_summary(summary))

if result.get("merge_events"):
    print("\nAuthor merge events:")
    for event in result["merge_events"]:
        print(
            f"  - Merged {event['merged_from']} into {event['kept']} "
            f"(similarity={event['similarity']:.4f})"
        )
