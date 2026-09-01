This repository is a lightweight authorship-attribution pipeline built around a streaming author profile tracker. The project is designed to process raw text, split it into sentence windows, encode those windows into style vectors, compare each vector to existing author profiles, and then optionally merge or smooth author assignments over time.

The implementation is intentionally modular: segmentation, encoding, profile matching, and smoothing are separated behind interfaces so different components can be swapped in independently.

## Repository layout

- `src/author_prediction/segmenter.py`  
  Sentence splitting and segment grouping heuristics.

- `src/author_prediction/interfaces.py`  
  Protocol definitions for the encoder and smoother.

- `src/author_prediction/profile_tracker.py`  
  Core logic for author matching and dynamic profile updates.

- `src/author_prediction/pipeline_implementation.py`  
  End-to-end orchestration of segmentation, encoding, matching, optional profile merging, and smoothing.

- `src/author_prediction/reporting.py`  
  Summary statistics for authored runs, change points, and profile activity.

- `src/author_prediction/deep_stylometry_encoder.py`  
  Adapter that wraps a DeepStylometry checkpoint so it satisfies the encoder interface.

- `src/author_prediction/dummy_encoder.py`  
  Deterministic hash-based encoder used for testing pipeline wiring without a real model.

- `src/author_prediction/smoothing.py`  
  Placeholder step-4 smoother. The default implementation is a no-op pass-through.

- `DeepStylometry/`  
  Submodule or workspace package containing the DeepStylometry model code and configs.

## High-level architecture

The pipeline follows four conceptual stages:

1. Segmentation and normalization
   - raw text is split into sentences
   - trailing sentences are grouped into a sliding context window

2. Encoding
   - each window is converted into a style vector by an encoder
   - the encoder returns a vector and token count

3. Author matching and profile tracking
   - vectors are compared to existing author centroids using cosine similarity
   - if similarity is low enough, a new author profile is created
   - otherwise the vector is assigned to the best existing author
   - the centroid is updated using an exponential moving average

4. Post-processing
   - similar profiles may be merged after the full pass
   - optional smoothing can be applied to reduce short noisy flips between authors

This is implemented in the `run_pipeline` function in `pipeline_implementation.py`.

## How the pipeline works in practice

The flow is:

```python
sentences = split_into_sentences(text)
for each sliding window over the sentence stream:
    window_text = " ".join(sentences[start : i + 1])
    vector, token_count = encoder.encode(window_text)
    result = tracker.step(vector, token_count, position=i)
    assignments.append(result)

id_remap = merge_similar_profiles(tracker, merge_threshold)
assignments = apply_id_remap(assignments, id_remap)
```

The `AuthorProfileTracker` maintains a dictionary of author profiles. Each profile has:

- an `author_id`
- a centroid vector `centroid`
- a `sample_count`
- a `last_seen` timestamp

The centroid represents the current best estimate of that author’s style vector.

flowchart TD
    User["User"] -->|Uploads text| FE["React Frontend"]
    FE -->|HTTP request| API["FastAPI Backend"]
    API -->|Store text| DB[("PostgreSQL")]
    API -->|Submit job| Queue["Worker Queue"]

    Queue -->|Job picked up| Worker["Worker Process (Python)"]
    Worker -->|Load text| DB

    Worker --> Tokenizer["ModernBERT Tokenizer"]
    Tokenizer --> Embedder["deep-stylometry-modernbert-mean Embedder"]
    Embedder --> Embedding["Text Embedding"]

    Embedding -->|Compare against| AuthorDB[("Author Style Embeddings (PostgreSQL)")]

    AuthorDB --> Decision{"Best match found?"}
    Decision -->|Yes, within threshold| Merge["Merge into matching author embedding"]
    Decision -->|No match| NewAuthor["Create new author embedding"]

    Merge --> AuthorDB
    NewAuthor --> AuthorDB
    

## Mathematical formulation

### 1. Normalization

Each encoded vector is converted to a unit vector before comparison:

$$
\mathbf{u} = \frac{\mathbf{x}}{\|\mathbf{x}\|_2}
$$

This ensures the matching step is based on direction, not magnitude. The code does this via `_to_unit_vector` in `profile_tracker.py`.

### 2. Cosine similarity

The tracker compares each incoming vector to each author centroid using cosine similarity:

$$
\text{sim}(\mathbf{c}, \mathbf{u}) = \mathbf{c} \cdot \mathbf{u}
$$

Because both vectors are unit-normalized, cosine similarity reduces to the dot product.

The system picks the best match:

$$
j^* = \arg\max_j \; \mathbf{c}_j \cdot \mathbf{u}
$$

If the best similarity is below the threshold `sim_threshold`, the algorithm creates a new author:

$$
\text{if } \max_j \text{sim}(\mathbf{c}_j, \mathbf{u}) < \tau_{\text{match}} \Rightarrow \text{new author}
$$

### 3. Exponential moving average update

For an existing author profile, the code updates the centroid with an EMA:

$$
\mathbf{c}_{t+1} = \alpha \mathbf{c}_t + (1-\alpha)\mathbf{u}_t
$$

where:

- $\mathbf{c}_t$ is the current centroid for that author
- $\mathbf{u}_t$ is the new incoming normalized vector
- $\alpha = \text{ema\_alpha}$

The code uses `self.ema_alpha` in `AuthorProfileTracker._update_profile`:

```python
blended = self.ema_alpha * profile.centroid + (1.0 - self.ema_alpha) * unit_vec
profile.centroid = blended / ||blended||
```

This is an exponential moving average on the vector direction, with a renormalization step so the centroid stays on the unit sphere.

The effect is that:

- a higher `ema_alpha` keeps the profile stable and slow to change
- a lower `ema_alpha` lets the profile adapt more quickly to new evidence

### 4. Profile merging

After the document has been processed, the system optionally consolidates authors with similar centroids using a separate merge threshold `merge_threshold`.

It computes cosine similarity between profile centroids:

$$
\text{sim}(\mathbf{c}_a, \mathbf{c}_b) = \mathbf{c}_a \cdot \mathbf{c}_b
$$

If this exceeds `merge_threshold`, it merges the two profiles.

The merge is not an EMA. It is a sample-weighted average of settled author centroids:

$$
\mathbf{c}_{\text{new}} = \frac{n_a \mathbf{c}_a + n_b \mathbf{c}_b}{n_a + n_b}
$$

where $n_a$ and $n_b$ are the profile sample counts. This is implemented in `merge_similar_profiles` in `pipeline_implementation.py`.

This is different from the online EMA because the merge step is applied after the whole run, when both profiles are already “settled” estimates rather than noisy single-window evidence.

### 5. Change-point detection

The reporting summary computes the locations where the assigned author changes between adjacent windows:

$$
\Delta_i = \mathbf{1}[a_i \neq a_{i-1}]
$$

This yields the change-point positions used in `reporting.py`.

## Why this is a plausible authorship model

The model uses a streaming, unsupervised nearest-centroid scheme:

- each author is represented by a centroid in embedding space
- new windows are assigned to the author whose style vector is closest in direction
- the centroid evolves over time to reflect the author’s stable style
- final profile merging repairs fragmentation when a single author was accidentally split into multiple profiles early in the run

This is a classic online clustering / centroid-tracking strategy for style attribution.

## Typical usage

### Install

Using `uv`:

```bash
uv sync
```

Using optional CUDA dependencies:

```bash
uv sync --extra cuda
# or
uv sync --extra cu124
```

### Minimal Python example

```python
import numpy as np
from author_prediction.profile_tracker import AuthorProfileTracker
from author_prediction.dummy_encoder import HashingDummyEncoder
from author_prediction.pipeline_implementation import run_pipeline

encoder = HashingDummyEncoder(dim=32)
tracker = AuthorProfileTracker(sim_threshold=0.65, ema_alpha=0.90)

text = "This is a sample document. It contains several sentences."
result = run_pipeline(text, encoder, tracker, context_window_size=3, stride=1)

print(result["assignments"])
print(result["profiles"])
```

This is a dependency-free way to exercise the pipeline before hooking in the DeepStylometry-backed encoder.

## Important implementation notes

- `sim_threshold` is the online matching threshold used during streaming.
- `merge_threshold` is the offline consolidation threshold used after processing.
- `min_tokens_for_update` prevents very short, noisy segments from distorting an author profile.
- `recency_decay` can penalize older profiles during matching, though it is optional.
- The `NoOpSmoother` in `smoothing.py` is a placeholder; real smoothing logic can be plugged in later without changing the rest of the pipeline.

## Summary

This repository implements a streaming, centroid-based authorship attribution system:

- segment text into windows
- encode into style vectors
- compare against author centroids using cosine similarity
- update centroids through EMA
- merge similar profiles after the fact
- summarize the resulting runs with reporting utilities

The mathematical heart of the model is a combination of cosine matching and exponential centroid updates, which together make it a practical online stylometric tracker.
