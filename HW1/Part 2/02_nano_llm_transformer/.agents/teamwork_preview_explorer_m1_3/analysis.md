# Milestone 1-3 Architecture Blueprint: Tokenizer, SFT & Device Management

## Executive Summary
This document provides the exhaustive implementation blueprint for three critical subsystems in `nano_transformer/`:
1. `nano_transformer/tokenizer.py`: Pure Python `ByteTokenizer` (256 UTF-8 bytes + 4 special tokens = 260 vocab size) and `BPETokenizer` (iterative byte pair encoding merges) with full diagnostic `inspect(text)` API returning token pieces, IDs, byte lengths, string offsets, and compression metrics.
2. `nano_transformer/sft.py`: Supervised Fine-Tuning primitives including `SFTDataset`, `DataCollatorForSFT` with prompt-masking (`ignore_index=-100`), autoregressive next-token prediction loss with sequence shift, lightweight `SFTTrainer`, and programmatic gradient flow verification (`verify_sft_gradient_flow`) across RoPE, SwiGLU, and RMSNorm.
3. `nano_transformer/device.py`: Apple Silicon auto-resolution (`mps` -> `cuda` -> `cpu`), unified host/Metal memory profiling (`get_memory_stats`), memory ceiling checks ($\le 4.0\text{ GB}$), and device synchronization primitives.

---

## 1. Tokenizer Subsystem (`nano_transformer/tokenizer.py`)

### 1.1 Architecture & Vocabulary Structure
To support arbitrary UTF-8 text without out-of-vocabulary (`<unk>`) errors while matching `ModelArgs.vocab_size = 260`, the tokenizer maps the 256 fundamental byte values `0x00 .. 0xFF` with an offset of 4, reserving indices 0..3 for special control tokens:
- Index `0`: `<pad>` (Padding token)
- Index `1`: `<bos>` (Beginning-of-sequence token)
- Index `2`: `<eos>` (End-of-sequence token)
- Index `3`: `<unk>` (Unknown/unmapped token fallback)
- Indices `4 .. 259`: Byte values `0 .. 255` (where token index = `byte_value + 4`)

### 1.2 ByteTokenizer Specification
```python
"""
nano_transformer/tokenizer.py
Implements ByteTokenizer and BPETokenizer with full introspection API.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import json
import os

SPECIAL_TOKENS = {
    "<pad>": 0,
    "<bos>": 1,
    "<eos>": 2,
    "<unk>": 3,
}
INV_SPECIAL_TOKENS = {v: k for k, v in SPECIAL_TOKENS.items()}
BYTE_OFFSET = 4
DEFAULT_VOCAB_SIZE = 260


class ByteTokenizer:
    """
    Pure Python UTF-8 Byte-level Tokenizer.
    Guarantees lossless round-trip encoding/decoding for any valid Unicode or byte sequence.
    """
    def __init__(self, vocab_size: int = DEFAULT_VOCAB_SIZE):
        self.vocab_size = vocab_size
        self.special_tokens = dict(SPECIAL_TOKENS)
        self.inv_special_tokens = dict(INV_SPECIAL_TOKENS)
        self.byte_offset = BYTE_OFFSET
        
        self.pad_token_id = SPECIAL_TOKENS["<pad>"]
        self.bos_token_id = SPECIAL_TOKENS["<bos>"]
        self.eos_token_id = SPECIAL_TOKENS["<eos>"]
        self.unk_token_id = SPECIAL_TOKENS["<unk>"]

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> List[int]:
        """
        Encodes a string into a list of token IDs.
        """
        if not text and not add_bos and not add_eos:
            return []
            
        byte_data = text.encode("utf-8")
        tokens = [b + self.byte_offset for b in byte_data]
        
        if add_bos:
            tokens = [self.bos_token_id] + tokens
        if add_eos:
            tokens = tokens + [self.eos_token_id]
        return tokens

    def decode(self, tokens: List[int], skip_special_tokens: bool = True) -> str:
        """
        Decodes a list of token IDs back into a Unicode string.
        """
        byte_list = []
        for t in tokens:
            if t in self.inv_special_tokens:
                if not skip_special_tokens:
                    # Append special token representation if not skipping
                    byte_list.extend(self.inv_special_tokens[t].encode("utf-8"))
            elif self.byte_offset <= t < self.vocab_size:
                byte_list.append(t - self.byte_offset)
            else:
                # Handle unexpected token id gracefully
                if not skip_special_tokens:
                    byte_list.extend(b"<unk>")
                    
        return bytes(byte_list).decode("utf-8", errors="replace")

    def inspect(self, text: str) -> Dict[str, Any]:
        """
        Produces detailed tokenization diagnostics for the admin dashboard.
        Returns:
            tokens: List of visual token piece representations
            token_ids: List of integer token IDs
            byte_lengths: List of byte sizes for each token
            offsets: List of [start_char, end_char] character spans
            compression_ratio: Raw UTF-8 bytes / Token count
            total_bytes: Total UTF-8 byte count
            total_tokens: Total token count
        """
        if not text:
            return {
                "tokens": [],
                "token_ids": [],
                "byte_lengths": [],
                "offsets": [],
                "compression_ratio": 0.0,
                "total_bytes": 0,
                "total_tokens": 0,
                "vocab_size": self.vocab_size,
            }
            
        token_ids = self.encode(text, add_bos=False, add_eos=False)
        total_bytes = len(text.encode("utf-8"))
        total_tokens = len(token_ids)
        compression_ratio = total_bytes / max(total_tokens, 1)
        
        # Build token representations, byte lengths, and character offsets
        tokens = []
        byte_lengths = []
        offsets = []
        
        # In byte tokenizer, each byte is a token. We map character spans:
        char_idx = 0
        current_byte_buffer = bytearray()
        
        for idx, t in enumerate(token_ids):
            byte_val = t - self.byte_offset
            byte_lengths.append(1)
            # Printable ASCII or hex representation
            if 32 <= byte_val <= 126 and byte_val != 92: # printable, not backslash
                tokens.append(chr(byte_val))
            else:
                tokens.append(f"\\x{byte_val:02x}")
                
            # Compute character offset
            # Map UTF-8 byte index to character index in original string
            # For simplicity, byte offset span:
            offsets.append([idx, idx + 1])

        return {
            "tokens": tokens,
            "token_ids": token_ids,
            "byte_lengths": byte_lengths,
            "offsets": offsets,
            "compression_ratio": round(compression_ratio, 4),
            "total_bytes": total_bytes,
            "total_tokens": total_tokens,
            "vocab_size": self.vocab_size,
        }
```

### 1.3 BPETokenizer (Byte-Pair Encoding Extension)
```python
class BPETokenizer(ByteTokenizer):
    """
    Byte-Pair Encoding Tokenizer trained on subword frequency statistics.
    Inherits ByteTokenizer base mapping and supports iterative merges.
    """
    def __init__(self, vocab_size: int = 512):
        super().__init__(vocab_size=DEFAULT_VOCAB_SIZE)
        self.target_vocab_size = vocab_size
        self.merges: Dict[Tuple[int, int], int] = {}
        self.vocab: Dict[int, bytes] = {
            i + self.byte_offset: bytes([i]) for i in range(256)
        }
        for name, idx in self.special_tokens.items():
            self.vocab[idx] = name.encode("utf-8")

    def train(self, corpus: Union[str, List[str]], target_vocab_size: int):
        """
        Trains BPE merges on input corpus up to target_vocab_size.
        """
        if isinstance(corpus, list):
            corpus = " ".join(corpus)
            
        initial_tokens = [b + self.byte_offset for b in corpus.encode("utf-8")]
        num_merges = target_vocab_size - len(self.vocab)
        
        ids = list(initial_tokens)
        curr_id = max(self.vocab.keys()) + 1
        
        for _ in range(max(0, num_merges)):
            # Count adjacent pairs
            pair_counts: Dict[Tuple[int, int], int] = {}
            for pair in zip(ids[:-1], ids[1:]):
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
            if not pair_counts:
                break
            best_pair = max(pair_counts, key=pair_counts.get)
            if pair_counts[best_pair] < 2:
                break # Stop if no pair occurs at least twice
                
            # Perform merge
            new_ids = []
            i = 0
            while i < len(ids):
                if i < len(ids) - 1 and ids[i] == best_pair[0] and ids[i+1] == best_pair[1]:
                    new_ids.append(curr_id)
                    i += 2
                else:
                    new_ids.append(ids[i])
                    i += 1
            ids = new_ids
            self.merges[best_pair] = curr_id
            self.vocab[curr_id] = self.vocab[best_pair[0]] + self.vocab[best_pair[1]]
            curr_id += 1
            
        self.vocab_size = len(self.vocab)

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> List[int]:
        if not text and not add_bos and not add_eos:
            return []
        ids = [b + self.byte_offset for b in text.encode("utf-8")]
        
        # Apply merges in order of priority
        while len(ids) >= 2:
            # Find candidate merge with lowest target token id (first learned)
            stats = {pair: self.merges[pair] for pair in zip(ids[:-1], ids[1:]) if pair in self.merges}
            if not stats:
                break
            best_pair = min(stats, key=stats.get)
            idx = self.merges[best_pair]
            
            new_ids = []
            i = 0
            while i < len(ids):
                if i < len(ids) - 1 and ids[i] == best_pair[0] and ids[i+1] == best_pair[1]:
                    new_ids.append(idx)
                    i += 2
                else:
                    new_ids.append(ids[i])
                    i += 1
            ids = new_ids
            
        if add_bos:
            ids = [self.bos_token_id] + ids
        if add_eos:
            ids = ids + [self.eos_token_id]
        return ids

    def decode(self, tokens: List[int], skip_special_tokens: bool = True) -> str:
        byte_chunks = []
        for t in tokens:
            if t in self.inv_special_tokens:
                if not skip_special_tokens:
                    byte_chunks.append(self.inv_special_tokens[t].encode("utf-8"))
            elif t in self.vocab:
                byte_chunks.append(self.vocab[t])
            else:
                if not skip_special_tokens:
                    byte_chunks.append(b"<unk>")
        return b"".join(byte_chunks).decode("utf-8", errors="replace")

    def inspect(self, text: str) -> Dict[str, Any]:
        if not text:
            return {
                "tokens": [],
                "token_ids": [],
                "byte_lengths": [],
                "offsets": [],
                "compression_ratio": 0.0,
                "total_bytes": 0,
                "total_tokens": 0,
                "vocab_size": self.vocab_size,
            }
        token_ids = self.encode(text, add_bos=False, add_eos=False)
        total_bytes = len(text.encode("utf-8"))
        total_tokens = len(token_ids)
        compression_ratio = total_bytes / max(total_tokens, 1)
        
        tokens = []
        byte_lengths = []
        offsets = []
        curr_offset = 0
        
        for t in token_ids:
            chunk = self.vocab.get(t, b"")
            byte_lengths.append(len(chunk))
            try:
                decoded_piece = chunk.decode("utf-8")
            except UnicodeDecodeError:
                decoded_piece = repr(chunk)
            tokens.append(decoded_piece)
            
            # Approximate character/byte span
            start = curr_offset
            end = curr_offset + len(decoded_piece)
            offsets.append([start, end])
            curr_offset = end

        return {
            "tokens": tokens,
            "token_ids": token_ids,
            "byte_lengths": byte_lengths,
            "offsets": offsets,
            "compression_ratio": round(compression_ratio, 4),
            "total_bytes": total_bytes,
            "total_tokens": total_tokens,
            "vocab_size": self.vocab_size,
        }
```

---

## 2. Supervised Fine-Tuning Subsystem (`nano_transformer/sft.py`)

### 2.1 Mathematical Formulation of SFT Loss & Prompt Masking
In autoregressive instruction fine-tuning, the objective is to maximize the likelihood of the response tokens conditioned on the prompt tokens.
Given sequence $X = [x_1, \dots, x_P, x_{P+1}, \dots, x_T]$ where $x_1 \dots x_P$ are prompt tokens and $x_{P+1} \dots x_T$ are response tokens:
$$\mathcal{L}_{SFT}(\theta) = -\frac{1}{T - P} \sum_{t=P+1}^{T} \log P_\theta(x_t \mid x_{<t})$$
To implement this in pure PyTorch:
1. Target labels $Y = [y_1, \dots, y_T]$ are constructed such that:
   $$y_t = \begin{cases} -100 & \text{for } 1 \le t \le P \text{ (Prompt tokens)} \\ x_t & \text{for } P+1 \le t \le T \text{ (Response tokens)} \end{cases}$$
2. The sequence is shifted for next-token prediction:
   $$\hat{L} = \text{Logits}[:, :-1, :] \quad (\text{shape: } B \times (T-1) \times V)$$
   $$\hat{Y} = Y[:, 1:] \quad (\text{shape: } B \times (T-1))$$
3. Standard PyTorch `nn.CrossEntropyLoss(ignore_index=-100)` ignores all targets where $\hat{Y}_{b, t} = -100$.

### 2.2 SFT Specification
```python
"""
nano_transformer/sft.py
Supervised Fine-Tuning dataset collation, prompt-masking, loss calculation, and gradient verification.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from nano_transformer.tokenizer import ByteTokenizer


class SFTDataset(Dataset):
    """
    Dataset wrapping (prompt, response) pairs into prompt-masked input_ids and labels.
    """
    def __init__(
        self,
        samples: List[Union[Tuple[str, str], Dict[str, str]]],
        tokenizer: ByteTokenizer,
        max_seq_len: int = 512,
        add_bos: bool = True,
        add_eos: bool = True,
    ):
        self.tokenizer = tokenizer
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
            # Prompt tokens are masked with -100
            labels = [-100] * len(prompt_ids) + response_ids
            
            # Truncate to max_seq_len
            if len(input_ids) > self.max_seq_len:
                input_ids = input_ids[:self.max_seq_len]
                labels = labels[:self.max_seq_len]
                
            self.data.append({
                "input_ids": input_ids,
                "labels": labels,
                "prompt_len": len(prompt_ids),
                "response_len": len(response_ids),
            })

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.data[idx]


class DataCollatorForSFT:
    """
    Batches, pads input_ids with pad_token_id, and pads labels with -100 (ignore_index).
    """
    def __init__(
        self,
        pad_token_id: int = 0,
        ignore_index: int = -100,
        max_seq_len: Optional[int] = None,
    ):
        self.pad_token_id = pad_token_id
        self.ignore_index = ignore_index
        self.max_seq_len = max_seq_len

    def __call__(self, batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        batch_max_len = max(len(x["input_ids"]) for x in batch)
        if self.max_seq_len is not None:
            batch_max_len = min(batch_max_len, self.max_seq_len)
            
        padded_inputs = []
        padded_labels = []
        attention_masks = []
        
        for item in batch:
            ids = item["input_ids"][:batch_max_len]
            lbls = item["labels"][:batch_max_len]
            
            pad_len = batch_max_len - len(ids)
            padded_ids = ids + [self.pad_token_id] * pad_len
            padded_lbl = lbls + [self.ignore_index] * pad_len
            mask = [1] * len(ids) + [0] * pad_len
            
            padded_inputs.append(padded_ids)
            padded_labels.append(padded_lbl)
            attention_masks.append(mask)
            
        return {
            "input_ids": torch.tensor(padded_inputs, dtype=torch.long),
            "labels": torch.tensor(padded_labels, dtype=torch.long),
            "attention_mask": torch.tensor(attention_masks, dtype=torch.float32),
        }


def compute_sft_loss(
    logits: torch.Tensor,
    labels: torch.Tensor,
    ignore_index: int = -100,
    reduction: str = "mean",
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """
    Computes autoregressive SFT loss with prompt-masking.
    Shift logits and labels:
        shift_logits = logits[:, :-1, :]
        shift_labels = labels[:, 1:]
    """
    shift_logits = logits[:, :-1, :].contiguous()
    shift_labels = labels[:, 1:].contiguous()
    
    vocab_size = shift_logits.size(-1)
    
    # Check if there are active (unmasked) target tokens
    valid_tokens = (shift_labels != ignore_index).sum()
    if valid_tokens == 0:
        # Avoid NaN when all targets are masked
        dummy_loss = (shift_logits * 0.0).sum()
        return dummy_loss, {"loss": 0.0, "perplexity": 1.0, "num_active_tokens": 0}
        
    loss = F.cross_entropy(
        shift_logits.view(-1, vocab_size),
        shift_labels.view(-1),
        ignore_index=ignore_index,
        reduction=reduction,
    )
    
    loss_val = float(loss.item())
    perplexity = float(torch.exp(torch.clamp(loss.detach(), max=100.0)).item())
    
    metrics = {
        "loss": loss_val,
        "perplexity": perplexity,
        "num_active_tokens": int(valid_tokens.item()),
    }
    return loss, metrics


class SFTTrainer:
    """
    Lightweight training harness for SFT fine-tuning.
    """
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        dataloader: DataLoader,
        device: torch.device,
        grad_clip: float = 1.0,
    ):
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
        loss, metrics = compute_sft_loss(logits, labels)
        
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
    """
    Verifies that gradients backpropagate through ALL custom components:
    - Embeddings & LM Head
    - Rotary Position Embeddings (RoPE) via wq/wk attention projections
    - SwiGLU Gated FeedForward Network (w_gate, w_up, w_down)
    - RMSNorm Pre-Normalization (attn_norm, ffn_norm, output_norm)
    """
    if tokenizer is None:
        tokenizer = ByteTokenizer()
    if device is None:
        device = next(model.parameters()).device
        
    model.train()
    model.zero_grad()
    
    prompt = "Instruction: Calculate 2 + 2."
    response = "Answer: 4."
    
    dataset = SFTDataset([(prompt, response)], tokenizer=tokenizer)
    collator = DataCollatorForSFT(pad_token_id=tokenizer.pad_token_id)
    batch = collator([dataset[0]])
    
    input_ids = batch["input_ids"].to(device)
    labels = batch["labels"].to(device)
    
    logits, _ = model(input_ids)
    loss, metrics = compute_sft_loss(logits, labels)
    loss.backward()
    
    components = {
        "tok_embeddings": False,
        "rope_attention_wq_wk": False,
        "swiglu_ffn": False,
        "rmsnorm": False,
        "output_norm": False,
    }
    
    param_reports = {}
    all_passed = True
    
    for name, p in model.named_parameters():
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
        
        # Verify specific subsystem gradients
        if "tok_embeddings" in name and has_grad and grad_norm > 0:
            components["tok_embeddings"] = True
        if ("wq" in name or "wk" in name) and has_grad and grad_norm > 0:
            components["rope_attention_wq_wk"] = True
        if ("w_gate" in name or "w_up" in name or "w_down" in name) and has_grad and grad_norm > 0:
            components["swiglu_ffn"] = True
        if ("attn_norm" in name or "ffn_norm" in name) and has_grad and grad_norm > 0:
            components["rmsnorm"] = True
        if "norm.weight" in name and has_grad and grad_norm > 0:
            components["output_norm"] = True

    return {
        "all_passed": all_passed and all(components.values()),
        "loss": float(loss.item()),
        "components_verified": components,
        "param_reports": param_reports,
    }
```

---

## 3. Device Management Subsystem (`nano_transformer/device.py`)

### 3.1 Hardware Architecture & Apple Silicon MPS Support
Apple Silicon Macs (M1/M2/M3/M4) feature a unified memory architecture where CPU cores and GPU cores share high-bandwidth physical LPDDR memory. In PyTorch:
- Device `"mps"` routes tensor math to Apple Metal Performance Shaders.
- `torch.backends.mps.is_available()` and `torch.backends.mps.is_built()` query Metal driver availability.
- `torch.mps.current_allocated_memory()` queries actively held Metal tensor buffers.
- `torch.mps.driver_allocated_memory()` queries Metal driver resident buffers.
- `psutil.virtual_memory()` and `psutil.Process().memory_info().rss` capture system-wide and process-level RAM occupancy.

### 3.2 Device Specification
```python
"""
nano_transformer/device.py
Apple Silicon MPS auto-resolution and unified memory profiling utilities.
"""

from typing import Dict, Any, Optional, Union
import os
import platform
import psutil
import torch


def resolve_device(preferred: Optional[str] = None) -> torch.device:
    """
    Resolves the execution device. Automatically defaults to Apple Silicon 'mps'
    if available on macOS, falling back to 'cuda' or 'cpu'.
    """
    if preferred is not None and preferred != "auto":
        pref = preferred.lower().strip()
        if pref == "mps":
            if torch.backends.mps.is_available() and torch.backends.mps.is_built():
                return torch.device("mps")
            # If MPS was explicitly requested but unavailable, fallback with warning
            return torch.device("cpu")
        elif pref == "cuda":
            if torch.cuda.is_available():
                return torch.device("cuda")
            return torch.device("cpu")
        elif pref == "cpu":
            return torch.device("cpu")
        else:
            return torch.device(pref)
            
    # Auto-resolution priority:
    # 1. Apple Silicon MPS
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    # 2. NVIDIA CUDA
    if torch.cuda.is_available():
        return torch.device("cuda")
    # 3. CPU
    return torch.device("cpu")


def get_memory_stats(device: Optional[Union[str, torch.device]] = None) -> Dict[str, Any]:
    """
    Collects comprehensive host and GPU memory metrics in Gigabytes (GB).
    Returns:
        ram_total_gb: System total physical RAM
        ram_used_gb: System used physical RAM
        ram_available_gb: System available physical RAM
        process_rss_gb: Current Python process Resident Set Size
        mps_allocated_gb: Metal/MPS memory allocated to PyTorch tensors
        mps_driver_gb: Metal driver allocated memory
        cuda_allocated_gb: CUDA memory allocated (if on CUDA)
        device: Active device string ('mps', 'cuda', 'cpu')
        mps_available: Whether MPS is available on host
        platform: OS and architecture platform string
    """
    if device is None:
        dev = resolve_device()
    elif isinstance(device, str):
        dev = torch.device(device)
    else:
        dev = device

    vm = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    proc_mem = proc.memory_info()
    
    ram_total_gb = vm.total / (1024 ** 3)
    ram_used_gb = vm.used / (1024 ** 3)
    ram_available_gb = vm.available / (1024 ** 3)
    process_rss_gb = proc_mem.rss / (1024 ** 3)
    
    mps_allocated_gb = 0.0
    mps_driver_gb = 0.0
    cuda_allocated_gb = 0.0
    
    mps_available = bool(torch.backends.mps.is_available() and torch.backends.mps.is_built())
    
    if dev.type == "mps" and mps_available:
        try:
            if hasattr(torch.mps, "current_allocated_memory"):
                mps_allocated_gb = torch.mps.current_allocated_memory() / (1024 ** 3)
            if hasattr(torch.mps, "driver_allocated_memory"):
                mps_driver_gb = torch.mps.driver_allocated_memory() / (1024 ** 3)
        except Exception:
            pass
            
    if dev.type == "cuda" and torch.cuda.is_available():
        try:
            cuda_allocated_gb = torch.cuda.memory_allocated() / (1024 ** 3)
        except Exception:
            pass

    return {
        "ram_total_gb": round(ram_total_gb, 4),
        "ram_used_gb": round(ram_used_gb, 4),
        "ram_available_gb": round(ram_available_gb, 4),
        "process_rss_gb": round(process_rss_gb, 4),
        "mps_allocated_gb": round(mps_allocated_gb, 6),
        "mps_driver_gb": round(mps_driver_gb, 6),
        "cuda_allocated_gb": round(cuda_allocated_gb, 6),
        "device": str(dev),
        "mps_available": mps_available,
        "platform": f"{platform.system()} {platform.machine()}",
    }


def check_memory_limit(
    max_limit_gb: float = 4.0,
    device: Optional[Union[str, torch.device]] = None
) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Verifies that total process + device memory usage does not exceed max_limit_gb.
    Returns:
        (within_limit: bool, current_usage_gb: float, stats: Dict[str, Any])
    """
    stats = get_memory_stats(device)
    current_usage_gb = stats["process_rss_gb"] + stats["mps_allocated_gb"] + stats["cuda_allocated_gb"]
    within_limit = current_usage_gb <= max_limit_gb
    return within_limit, round(current_usage_gb, 4), stats


def sync_device(device: Optional[Union[str, torch.device]] = None):
    """
    Blocks until all asynchronous device operations have completed.
    Essential for accurate latency and throughput benchmarking.
    """
    if device is None:
        dev = resolve_device()
    elif isinstance(device, str):
        dev = torch.device(device)
    else:
        dev = device

    if dev.type == "mps":
        if hasattr(torch.mps, "synchronize"):
            torch.mps.synchronize()
    elif dev.type == "cuda":
        if torch.cuda.is_available():
            torch.cuda.synchronize()
```

---

## 4. Verification & Testing Blueprint

### 4.1 Tokenizer Unit Test Matrix
| Test Name | Target Behavior | Expected Result |
|---|---|---|
| `test_byte_tokenizer_ascii` | Encode & decode standard ASCII text | Perfect round-trip fidelity `decode(encode(s)) == s` |
| `test_byte_tokenizer_unicode` | Multi-byte characters (Emojis 🚀, CJK 你好, Cyrillic Привет) | Perfect round-trip fidelity across multi-byte UTF-8 boundaries |
| `test_byte_tokenizer_special_tokens` | Verify `<pad>=0`, `<bos>=1`, `<eos>=2`, `<unk>=3` | `encode("hi", add_bos=True, add_eos=True)` starts with 1, ends with 2 |
| `test_byte_tokenizer_inspect` | `inspect("Hello 🚀")` | Returns `tokens`, `token_ids`, `byte_lengths`, `offsets`, `compression_ratio` |
| `test_bpe_tokenizer_train_merge` | Train BPE on repetitive corpus | Subwords are merged; token count decreases; compression ratio > 1.0 |
| `test_tokenizer_empty_string` | `encode("")`, `decode([])`, `inspect("")` | Graceful zero-length handling without index errors |

### 4.2 SFT Unit Test Matrix
| Test Name | Target Behavior | Expected Result |
|---|---|---|
| `test_sft_dataset_masking` | Create dataset from (prompt, response) pairs | Labels have `-100` across all prompt tokens, actual tokens for response |
| `test_sft_collator_padding` | Collate variable length sequences | Input IDs padded with 0, Labels padded with -100, Attention mask is 0/1 |
| `test_sft_loss_shift` | Compute autoregressive loss | Logits shifted `[:-1]`, labels shifted `[1:]`, loss only on unmasked tokens |
| `test_sft_loss_all_masked` | Compute loss when all labels are -100 | Returns 0.0 scalar loss without NaN |
| `test_sft_gradient_flow` | `verify_sft_gradient_flow(model)` | Non-zero finite gradients in embeddings, RoPE, SwiGLU, RMSNorm |

### 4.3 Device Unit Test Matrix
| Test Name | Target Behavior | Expected Result |
|---|---|---|
| `test_resolve_device_auto` | Auto-detect device on macOS | Returns `device(type='mps')` when Apple Silicon available |
| `test_resolve_device_override` | Force `resolve_device('cpu')` | Returns `device(type='cpu')` |
| `test_get_memory_stats` | Query system and Metal memory | Dict contains valid float keys `ram_total_gb`, `process_rss_gb`, etc. |
| `test_check_memory_limit` | Enforce 4.0 GB limit | Returns `(True, used_gb, stats)` when under 4.0 GB |
| `test_sync_device` | Call `sync_device('mps')` and `sync_device('cpu')` | Executes without exceptions |
