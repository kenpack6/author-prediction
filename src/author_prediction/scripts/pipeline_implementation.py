import torch
import torch.nn.functional as F
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer
from pathlib import Path
from deep_stylometry.modules.modeling_deep_stylometry import DeepStylometry
from deep_stylometry.utils.configs import BaseConfig


class OnlineAuthorDiarizer:
    def __init__(
        self,
        checkpoint_repo: str = "Madjakul/deep-stylometry-modernbert-mean",
        config_path: str = "DeepStylometry/configs/test_mean.yml",
        sim_threshold: float = 0.65,      # Threshold above which text matches an existing author
        ema_alpha: float = 0.90,          # Weight for existing profile (1 - alpha for new input)
        context_window_size: int = 3,     # Window of sentences to provide sufficient stylistic entropy
        min_tokens_for_update: int = 15,  # Avoid polluting profile with 2-word sentences
        device: str = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.device = device
        self.sim_threshold = sim_threshold
        self.ema_alpha = ema_alpha
        self.context_window_size = context_window_size
        self.min_tokens_for_update = min_tokens_for_update

        # 1. Load DeepStylometry Model
        print(f"Loading checkpoint from {checkpoint_repo} on {self.device}...")
        checkpoint_path = hf_hub_download(repo_id=checkpoint_repo, filename="last.ckpt")
        cfg = BaseConfig(mode="test").from_yaml(config_path)
        self.model = DeepStylometry.load_from_checkpoint(checkpoint_path, cfg=cfg)
        self.model.to(self.device)
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")
        
        # State: Author ID -> {"centroid": Tensor, "sample_count": int, "last_seen": int}
        self.author_profiles = {}
        self.next_author_id = 1

    @torch.no_grad()
    def encode_text(self, text: str) -> torch.Tensor:
        """Encodes text snippet into a normalized mean-pooled stylistic vector."""
        enc = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)

        # (1, seq_len, 768)
        token_embs = self.model(enc["input_ids"], enc["attention_mask"])
        mask = enc["attention_mask"].unsqueeze(-1)
        
        # Masked mean pooling & L2 normalization
        pooled = (token_embs * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        unit_vec = F.normalize(pooled, p=2, dim=-1) # (1, 768)
        return unit_vec.squeeze(0)

    def process_document(self, sentences: list[str]) -> list[dict]:
        """Processes document sentence by sentence and identifies author shifts."""
        results = []
        n_sentences = len(sentences)

        for i, sentence in enumerate(sentences):
            # Form rolling context window around sentence i to give model enough stylistic surface
            start_idx = max(0, i - self.context_window_size + 1)
            window_text = " ".join(sentences[start_idx : i + 1])
            
            vec = self.encode_text(window_text)
            token_count = len(self.tokenizer.tokenize(sentence))

            assigned_author = None
            best_sim = -1.0

            if not self.author_profiles:
                # First author
                assigned_author = f"Author_{self.next_author_id}"
                self.next_author_id += 1
                self.author_profiles[assigned_author] = {
                    "centroid": vec,
                    "sample_count": 1,
                    "last_seen": i
                }
            else:
                # Compare against current author profiles
                author_keys = list(self.author_profiles.keys())
                centroids = torch.stack([self.author_profiles[k]["centroid"] for k in author_keys]) # (K, 768)
                
                # Cosine similarities
                sims = torch.matmul(centroids, vec) # (K,)
                max_sim, best_idx = torch.max(sims, dim=0)
                best_sim = max_sim.item()
                best_match_author = author_keys[best_idx.item()]

                if best_sim >= self.sim_threshold:
                    assigned_author = best_match_author
                    # Update author profile if sentence is sufficiently long/informative
                    if token_count >= self.min_tokens_for_update:
                        curr_centroid = self.author_profiles[assigned_author]["centroid"]
                        updated = self.ema_alpha * curr_centroid + (1 - self.ema_alpha) * vec
                        self.author_profiles[assigned_author]["centroid"] = F.normalize(updated, p=2, dim=-1)
                        self.author_profiles[assigned_author]["sample_count"] += 1
                        self.author_profiles[assigned_author]["last_seen"] = i
                else:
                    # New author detected
                    assigned_author = f"Author_{self.next_author_id}"
                    self.next_author_id += 1
                    self.author_profiles[assigned_author] = {
                        "centroid": vec,
                        "sample_count": 1,
                        "last_seen": i
                    }

            # Check if speaker changed from previous sentence
            is_change = (i > 0 and results[i - 1]["author"] != assigned_author)

            results.append({
                "sentence_idx": i,
                "text": sentence,
                "author": assigned_author,
                "similarity_to_matched": best_sim,
                "author_changed": is_change,
            })

        return results
