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

DATA_PATH = "src/author_prediction/data/data_orth.txt"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    text = f.read()

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
)

summary = summarize_run(result)
print(format_run_summary(summary))
