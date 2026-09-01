"""Encoder adapter wrapping the real DeepStylometry checkpoint (step 2),
so it satisfies EncoderProtocol and plugs directly into
pipeline_implementation.run_pipeline.

UNVERIFIED: the exact call signature of DeepStylometry.forward() -- in
particular whether it returns per-token hidden states of shape
(batch, seq_len, hidden_dim) as assumed by the masked-mean-pooling code
below -- has not been confirmed against modeling_deep_stylometry.py in
this session. This module could not be run or tested in this sandbox
(no network access to Hugging Face, no deep_stylometry package
installed here). Run it yourself and verify the output vector shape and
a couple of known similar/dissimilar text pairs before trusting it in
the full pipeline. A shape mismatch here would fail silently -- it
would not raise an error, it would just produce meaningless vectors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

from deep_stylometry.modules.modeling_deep_stylometry import DeepStylometry
from deep_stylometry.utils.configs import BaseConfig


class DeepStylometryEncoder:
    """Wraps a DeepStylometry checkpoint to satisfy EncoderProtocol.

    Unlike the original OnlineAuthorDiarizer reference implementation,
    this class does NOT manage the sliding context window itself --
    run_pipeline already does that (it joins trailing sentences before
    calling encode()). This class's only job is: given a text span,
    return a normalized style vector and its token count.

    Args:
        checkpoint_repo: Hugging Face repo id for the checkpoint.
        config_path: Path to the model's YAML config, relative to
            wherever this is instantiated from (matches the
            reference implementation's usage).
        max_length: Max tokens per span before truncation.
        device: Torch device string. Auto-detects cuda/mps/cpu if
            omitted.
    """

    @staticmethod
    def _resolve_config_path(config_path: str) -> str:
        """Resolve config locations relative to the repo/submodule root."""
        path = Path(config_path)
        if path.is_absolute():
            return str(path)

        candidates = [
            Path.cwd() / path,
            Path(__file__).resolve().parents[2] / path,
            Path(__file__).resolve().parents[2] / "DeepStylometry" / path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return str(Path.cwd() / path)

    def __init__(
        self,
        checkpoint_repo: str = "Madjakul/deep-stylometry-modernbert-mean",
        config_path: str = "configs/test_mean.yml",
        max_length: int = 512,
        device: Optional[str] = None,
    ) -> None:
        self.device = device or (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self.max_length = max_length
        self.config_path = self._resolve_config_path(config_path)

        checkpoint_path = hf_hub_download(repo_id=checkpoint_repo, filename="last.ckpt")
        cfg = BaseConfig(mode="test").from_yaml(self.config_path)
        self.model = DeepStylometry.load_from_checkpoint(checkpoint_path, cfg=cfg)
        self.model.to(self.device)
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")

    @torch.no_grad()
    def encode(self, text: str) -> Tuple[np.ndarray, int]:
        """Encode a text span into a normalized style vector.

        Args:
            text: The span to encode (already windowed by the caller).

        Returns:
            ``(vector, token_count)`` -- a unit-norm numpy vector and
            the number of real (non-padding) tokens the span consumed.
        """
        enc = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(self.device)

        # ASSUMED shape: (1, seq_len, hidden_dim). Verify this against
        # the real forward() signature -- see module docstring.
        token_embs = self.model(enc["input_ids"], enc["attention_mask"])

        mask = enc["attention_mask"].unsqueeze(-1)
        pooled = (token_embs * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        unit_vec = F.normalize(pooled, p=2, dim=-1).squeeze(0)

        token_count = int(enc["attention_mask"].sum().item())
        return unit_vec.cpu().numpy(), token_count
