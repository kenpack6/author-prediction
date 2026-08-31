# Author Prediction

Authorship attribution and stylometry models workspace.

## Installation

### Using `uv` (Recommended)

- **Default installation**:
  ```bash
  uv sync
  ```

- **Install with PyTorch CUDA wheels**:
  ```bash
  uv sync --extra cuda
  # or
  uv sync --extra cu124
  ```

### Using `pip`

- **Install with PyTorch CUDA wheels**:
  ```bash
  pip install .[cuda] --extra-index-url https://download.pytorch.org/whl/cu124
  ```
