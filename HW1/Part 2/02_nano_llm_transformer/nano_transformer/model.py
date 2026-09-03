"""Full Autoregressive Transformer Model with RoPE, SwiGLU, RMSNorm, and KV-Cache."""

import time
from typing import List, Optional, Tuple, Union, Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

from nano_transformer.config import ModelArgs
from nano_transformer.norm import RMSNorm
from nano_transformer.block import TransformerBlock
from nano_transformer.attention import KVCache


class Transformer(nn.Module):
    """Pure PyTorch Autoregressive Decoder-only Transformer."""

    def __init__(self, args: ModelArgs) -> None:
        super().__init__()
        self.args = args
        self.vocab_size = args.vocab_size
        self.n_layers = args.n_layers

        # Token Embeddings
        self.tok_embeddings = nn.Embedding(args.vocab_size, args.d_model)

        # Transformer Blocks
        self.layers = nn.ModuleList([
            TransformerBlock(args, layer_idx=i) for i in range(args.n_layers)
        ])

        # Final RMSNorm
        self.norm = RMSNorm(args.d_model, eps=args.norm_eps)

        # Output LM Head (bias-free)
        self.lm_head = nn.Linear(args.d_model, args.vocab_size, bias=False)

        # Weight Tying
        if args.tie_embeddings:
            self.lm_head.weight = self.tok_embeddings.weight

        # Parameter initialization
        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        """Initializes linear and embedding weights with small gaussian standard deviation."""
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def reset_cache(self) -> None:
        """Resets KV caches across all transformer layers."""
        for layer in self.layers:
            layer.attention.reset_cache()

    def forward(
        self,
        tokens: torch.Tensor,
        start_pos: int = 0,
        kv_cache: Optional[List[KVCache]] = None,
        use_cache: bool = False,
        return_attentions: bool = False,
        targets: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Optional[Any]]:
        """Forward pass for the full Transformer.

        Args:
            tokens: Tensor of token IDs of shape (B, T).
            start_pos: Starting position for RoPE frequency slicing.
            kv_cache: Optional list of KVCache objects (one per layer).
            use_cache: Whether to use KV caching.
            return_attentions: Whether to collect and return attention weight heatmaps.
            targets: Optional ground-truth target tokens for SFT loss computation.

        Returns:
            Tuple of (logits tensor of shape (B, T, vocab_size), optional loss or attention matrices).
        """
        B, T = tokens.shape

        h = self.tok_embeddings(tokens)

        all_attentions = [] if return_attentions else None

        for i, layer in enumerate(self.layers):
            layer_kv = kv_cache[i] if kv_cache is not None else None
            h, attn_w = layer(
                h,
                start_pos=start_pos,
                kv_cache=layer_kv,
                use_cache=use_cache,
                return_attentions=return_attentions
            )
            if return_attentions and attn_w is not None:
                all_attentions.append(attn_w)

        h = self.norm(h)
        logits = self.lm_head(h)

        if targets is not None:
            # Shift for autoregressive next-token prediction
            if logits.shape[1] == targets.shape[1]:
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = targets[:, 1:].contiguous()
            else:
                shift_logits = logits.contiguous()
                shift_labels = targets.contiguous()
            
            loss = F.cross_entropy(
                shift_logits.view(-1, self.vocab_size),
                shift_labels.view(-1),
                ignore_index=-100
            )
            return logits, loss

        if return_attentions:
            return logits, all_attentions

        return logits, None

    @torch.no_grad()
    def generate(
        self,
        prompt_tokens: Union[List[int], torch.Tensor],
        max_new_tokens: int = 50,
        temperature: float = 0.8,
        top_k: int = 50,
        top_p: float = 0.9,
        device: Optional[Union[str, torch.device]] = None,
        return_metrics: bool = False,
        eos_id: Optional[int] = 2,
        use_cache: bool = True
    ) -> Union[List[int], Tuple[List[int], Dict[str, Any]]]:
        """Autoregressive text generation loop with dynamic KV-caching.

        Args:
            prompt_tokens: List or Tensor of prompt token IDs.
            max_new_tokens: Maximum number of new tokens to generate.
            temperature: Sampling temperature (lower = more deterministic).
            top_k: Top-k filtering cutoff.
            top_p: Nucleus sampling probability cutoff.
            device: Execution device.
            return_metrics: Whether to return generation throughput and latency metrics.
            eos_id: End-of-sequence token ID; pass None to disable early stopping.
            use_cache: Whether to use KV caching for O(1) single-token steps.

        Returns:
            List of generated token IDs (including prompt) or (tokens, metrics dict).
        """
        if device is None:
            device = next(self.parameters()).device
        elif isinstance(device, str):
            device = torch.device(device)

        # Ensure model is in eval mode on device
        self.eval()

        # Handle prompt formatting
        if isinstance(prompt_tokens, torch.Tensor):
            if prompt_tokens.dim() == 1:
                tokens_tensor = prompt_tokens.unsqueeze(0).to(device)
            else:
                tokens_tensor = prompt_tokens.to(device)
            tokens_list = tokens_tensor.squeeze(0).tolist()
        else:
            if not prompt_tokens:
                tokens_list = [1]  # Default to BOS
            else:
                tokens_list = list(prompt_tokens)
            tokens_tensor = torch.tensor([tokens_list], dtype=torch.long, device=device)

        if max_new_tokens <= 0:
            if return_metrics:
                return tokens_list, {"tokens_generated": 0, "elapsed_seconds": 0.0}
            return tokens_list

        t_start = time.perf_counter()
        kv_caches = [KVCache() for _ in range(self.n_layers)] if use_cache else None

        # 1. Prefill step
        B, S = tokens_tensor.shape
        logits, _ = self.forward(tokens_tensor, start_pos=0, kv_cache=kv_caches, use_cache=use_cache)
        next_logits = logits[:, -1, :]

        def sample_token(logits_1d: torch.Tensor) -> int:
            if temperature <= 0.0 or temperature < 1e-4:
                return int(torch.argmax(logits_1d, dim=-1).item())
            
            scaled_logits = logits_1d / temperature
            if top_k > 0:
                k_val = min(top_k, scaled_logits.size(-1))
                topk_vals, _ = torch.topk(scaled_logits, k_val)
                min_val = topk_vals[-1]
                scaled_logits = torch.where(
                    scaled_logits < min_val,
                    torch.full_like(scaled_logits, float("-inf")),
                    scaled_logits
                )
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(scaled_logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                indices_to_remove = sorted_indices[sorted_indices_to_remove]
                scaled_logits[indices_to_remove] = float("-inf")

            probs = F.softmax(scaled_logits, dim=-1)
            return int(torch.multinomial(probs, num_samples=1).item())

        first_token = sample_token(next_logits[0])
        generated = list(tokens_list) + [first_token]
        curr_token = torch.tensor([[first_token]], dtype=torch.long, device=device)

        # 2. Incremental single-token decoding steps
        for step in range(1, max_new_tokens):
            if eos_id is not None and generated[-1] == eos_id:
                break

            if use_cache:
                start_pos = S + step - 1
                logits, _ = self.forward(curr_token, start_pos=start_pos, kv_cache=kv_caches, use_cache=True)
                next_logits = logits[:, -1, :]
            else:
                full_input = torch.tensor([generated], dtype=torch.long, device=device)
                logits, _ = self.forward(full_input, start_pos=0, use_cache=False)
                next_logits = logits[:, -1, :]

            next_tok = sample_token(next_logits[0])
            generated.append(next_tok)
            curr_token = torch.tensor([[next_tok]], dtype=torch.long, device=device)

        t_end = time.perf_counter()
        elapsed = t_end - t_start
        gen_count = len(generated) - len(tokens_list)

        if return_metrics:
            metrics = {
                "tokens_generated": gen_count,
                "elapsed_seconds": round(elapsed, 4),
                "tokens_per_second": round(gen_count / max(elapsed, 1e-6), 2),
                "ms_per_token": round((elapsed / max(gen_count, 1)) * 1000.0, 2),
            }
            return generated, metrics

        return generated
