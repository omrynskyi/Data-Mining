"""Supervised Fine-Tuning (SFT) dataset collation, loss computation, and gradient verification."""

from typing import List, Dict, Any, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from nano_transformer.tokenizer import ByteTokenizer


class SFTDataset(Dataset):
    """Dataset wrapping (prompt, response) pairs with prompt masking (ignore_index=-100)."""

    def __init__(
        self,
        samples: List[Union[Tuple[str, str], Dict[str, str]]],
        tokenizer: Optional[ByteTokenizer] = None,
        max_seq_len: int = 512,
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> None:
        self.tokenizer = tokenizer if tokenizer is not None else ByteTokenizer()
        self.max_seq_len = max_seq_len
        self.data: List[Dict[str, Any]] = []

        for sample in samples:
            if isinstance(sample, tuple):
                prompt, response = sample
            elif isinstance(sample, dict):
                if "instruction" in sample and "output" in sample:
                    prompt = sample.get("instruction", "")
                    if sample.get("input"):
                        prompt += "\n" + sample["input"]
                    response = sample["output"]
                else:
                    prompt = sample.get("prompt", "")
                    response = sample.get("response", "")
            else:
                continue

            prompt_ids = self.tokenizer.encode(prompt, add_bos=add_bos, add_eos=False)
            response_ids = self.tokenizer.encode(response, add_bos=False, add_eos=add_eos)

            input_ids = prompt_ids + response_ids
            # Prompt tokens are masked with -100 for loss computation
            labels = [-100] * len(prompt_ids) + response_ids

            if len(input_ids) > self.max_seq_len:
                input_ids = input_ids[:self.max_seq_len]
                labels = labels[:self.max_seq_len]

            self.data.append({
                "input_ids": torch.tensor(input_ids, dtype=torch.long),
                "labels": torch.tensor(labels, dtype=torch.long),
                "prompt_len": len(prompt_ids),
                "response_len": len(response_ids),
            })

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.data[idx]


def collate_sft(
    batch: List[Dict[str, Any]],
    pad_token_id: int = 0,
    ignore_index: int = -100,
    max_seq_len: Optional[int] = None
) -> Dict[str, torch.Tensor]:
    """Collates and pads a batch of SFT samples."""
    max_len = max(len(x["input_ids"]) for x in batch)
    if max_seq_len is not None:
        max_len = min(max_len, max_seq_len)

    padded_inputs = []
    padded_labels = []
    attention_masks = []

    for item in batch:
        ids = item["input_ids"][:max_len]
        lbls = item["labels"][:max_len]

        if isinstance(ids, torch.Tensor):
            ids = ids.tolist()
        if isinstance(lbls, torch.Tensor):
            lbls = lbls.tolist()

        pad_len = max_len - len(ids)
        padded_ids = ids + [pad_token_id] * pad_len
        padded_lbl = lbls + [ignore_index] * pad_len
        mask = [1.0] * len(ids) + [0.0] * pad_len

        padded_inputs.append(padded_ids)
        padded_labels.append(padded_lbl)
        attention_masks.append(mask)

    return {
        "input_ids": torch.tensor(padded_inputs, dtype=torch.long),
        "labels": torch.tensor(padded_labels, dtype=torch.long),
        "attention_mask": torch.tensor(attention_masks, dtype=torch.float32),
    }


class DataCollatorForSFT:
    """Callable class wrapper for SFT batch collation."""

    def __init__(
        self,
        pad_token_id: int = 0,
        ignore_index: int = -100,
        max_seq_len: Optional[int] = None
    ) -> None:
        self.pad_token_id = pad_token_id
        self.ignore_index = ignore_index
        self.max_seq_len = max_seq_len

    def __call__(self, batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        return collate_sft(
            batch,
            pad_token_id=self.pad_token_id,
            ignore_index=self.ignore_index,
            max_seq_len=self.max_seq_len
        )


def compute_sft_loss(
    logits: torch.Tensor,
    labels: torch.Tensor,
    ignore_index: int = -100,
    reduction: str = "mean",
    return_metrics: bool = False
) -> Union[torch.Tensor, Tuple[torch.Tensor, Dict[str, Any]]]:
    """Computes autoregressive SFT loss with prompt-masking.

    Shifts logits and labels for next-token prediction:
        shift_logits = logits[:, :-1, :]
        shift_labels = labels[:, 1:]
    """
    if logits.shape[1] == labels.shape[1]:
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = labels[:, 1:].contiguous()
    else:
        shift_logits = logits.contiguous()
        shift_labels = labels.contiguous()

    vocab_size = shift_logits.size(-1)
    valid_tokens = (shift_labels != ignore_index).sum()

    if valid_tokens == 0:
        loss = (shift_logits * 0.0).sum()
        metrics = {"loss": 0.0, "perplexity": 1.0, "num_active_tokens": 0}
    else:
        loss = F.cross_entropy(
            shift_logits.view(-1, vocab_size),
            shift_labels.view(-1),
            ignore_index=ignore_index,
            reduction=reduction
        )
        loss_val = float(loss.item())
        perplexity = float(torch.exp(torch.clamp(loss.detach(), max=100.0)).item())
        metrics = {
            "loss": loss_val,
            "perplexity": perplexity,
            "num_active_tokens": int(valid_tokens.item()),
        }

    if return_metrics:
        return loss, metrics
    return loss


class SFTTrainer:
    """Lightweight training harness for SFT fine-tuning."""

    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        dataloader: DataLoader,
        device: torch.device,
        grad_clip: float = 1.0,
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.dataloader = dataloader
        self.device = device
        self.grad_clip = grad_clip
        self.step = 0

    def training_step(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        self.model.train()
        input_ids = batch["input_ids"].to(self.device)
        labels = batch["labels"].to(self.device)

        self.optimizer.zero_grad()
        logits, _ = self.model(input_ids)
        loss, metrics = compute_sft_loss(logits, labels, return_metrics=True)

        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()

        self.step += 1
        metrics["grad_norm"] = float(grad_norm.item() if isinstance(grad_norm, torch.Tensor) else grad_norm)
        metrics["step"] = self.step
        return metrics


def verify_sft_gradient_flow(
    model: nn.Module,
    tokenizer: Optional[ByteTokenizer] = None,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """Verifies that gradients backpropagate through all custom components:

    - Token Embeddings & LM Head
    - RoPE Attention Projections (q_proj, k_proj, v_proj, out_proj)
    - SwiGLU FFN Projections (w_gate, w_up, w_down)
    - RMSNorm Pre-Normalization (attention_norm, ffn_norm, final norm)
    """
    if tokenizer is None:
        tokenizer = ByteTokenizer()
    if device is None:
        device = next(model.parameters()).device

    model.train()
    model.zero_grad()

    prompt = "Instruction: Explain neural networks."
    response = "Answer: Neural networks are computing systems inspired by biological brains."

    dataset = SFTDataset([(prompt, response)], tokenizer=tokenizer)
    collator = DataCollatorForSFT(pad_token_id=tokenizer.pad_id)
    batch = collator([dataset[0]])

    input_ids = batch["input_ids"].to(device)
    labels = batch["labels"].to(device)

    logits, _ = model(input_ids)
    loss = compute_sft_loss(logits, labels)
    loss.backward()

    components = {
        "tok_embeddings": False,
        "rope_attention_projections": False,
        "swiglu_ffn_projections": False,
        "rmsnorm_layers": False,
        "output_norm": False,
    }

    param_reports = {}
    all_passed = True

    for name, p in model.named_parameters():
        if p.requires_grad:
            if p.grad is None:
                has_grad = False
                is_finite = False
                grad_norm = 0.0
                all_passed = False
            else:
                has_grad = True
                is_finite = not bool(torch.isnan(p.grad).any() or torch.isinf(p.grad).any())
                grad_norm = float(p.grad.norm().item())
                if not is_finite or grad_norm == 0.0:
                    all_passed = False

            param_reports[name] = {
                "has_grad": has_grad,
                "is_finite": is_finite,
                "grad_norm": grad_norm,
            }

            if "tok_embeddings" in name and has_grad and grad_norm > 0:
                components["tok_embeddings"] = True
            if any(k in name for k in ["q_proj", "k_proj", "v_proj", "out_proj", "wq", "wk", "wv", "wo"]) and has_grad and grad_norm > 0:
                components["rope_attention_projections"] = True
            if any(k in name for k in ["w_gate", "w_up", "w_down", "gate_proj", "up_proj", "down_proj"]) and has_grad and grad_norm > 0:
                components["swiglu_ffn_projections"] = True
            if any(k in name for k in ["attention_norm", "ffn_norm", "attn_norm"]) and has_grad and grad_norm > 0:
                components["rmsnorm_layers"] = True
            if "norm.weight" in name and has_grad and grad_norm > 0:
                components["output_norm"] = True

    return {
        "all_passed": all_passed and all(components.values()),
        "loss": float(loss.item()),
        "components_verified": components,
        "param_reports": param_reports,
    }
