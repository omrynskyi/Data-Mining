"""Pure Python UTF-8 ByteTokenizer and Subword BPETokenizer with Introspection API."""

from typing import List, Dict, Any, Optional, Tuple, Union

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
    """Pure Python UTF-8 Byte-level Tokenizer with complete OOV immunity.

    Maps 256 byte values 0..255 with an offset of +4, reserving 0..3 for special tokens.
    Total vocabulary size = 260.
    """

    def __init__(self, vocab_size: int = DEFAULT_VOCAB_SIZE) -> None:
        self.vocab_size = vocab_size
        self.special_tokens = dict(SPECIAL_TOKENS)
        self.inv_special_tokens = dict(INV_SPECIAL_TOKENS)
        self.byte_offset = BYTE_OFFSET

        # Standard ID properties
        self.pad_id = SPECIAL_TOKENS["<pad>"]
        self.bos_id = SPECIAL_TOKENS["<bos>"]
        self.eos_id = SPECIAL_TOKENS["<eos>"]
        self.unk_id = SPECIAL_TOKENS["<unk>"]

        # Aliases
        self.pad_token_id = self.pad_id
        self.bos_token_id = self.bos_id
        self.eos_token_id = self.eos_id
        self.unk_token_id = self.unk_id

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> List[int]:
        """Encodes a string into byte token IDs."""
        if not text:
            tokens: List[int] = []
        else:
            raw_bytes = text.encode("utf-8")
            tokens = [b + self.byte_offset for b in raw_bytes]

        if add_bos:
            tokens = [self.bos_id] + tokens
        if add_eos:
            tokens = tokens + [self.eos_id]

        return tokens

    def decode(self, tokens: List[int], skip_special_tokens: bool = True) -> str:
        """Decodes token IDs back into a Unicode string."""
        byte_list = bytearray()
        for t in tokens:
            if t in self.inv_special_tokens:
                if not skip_special_tokens:
                    byte_list.extend(self.inv_special_tokens[t].encode("utf-8"))
            elif self.byte_offset <= t < self.vocab_size:
                byte_list.append(t - self.byte_offset)
            else:
                if not skip_special_tokens:
                    byte_list.extend(b"<unk>")

        return byte_list.decode("utf-8", errors="replace")

    def inspect(self, text: str) -> Dict[str, Any]:
        """Produces comprehensive tokenization diagnostics for dashboard visualization."""
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

        tokens: List[str] = []
        byte_lengths: List[int] = []
        offsets: List[List[int]] = []

        for idx, t in enumerate(token_ids):
            byte_val = t - self.byte_offset
            byte_lengths.append(1)
            # Render printable ASCII characters or hex bytes
            if 32 <= byte_val <= 126 and byte_val != 92:
                tokens.append(chr(byte_val))
            else:
                tokens.append(f"\\x{byte_val:02x}")
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


class BPETokenizer(ByteTokenizer):
    """Byte-Pair Encoding Tokenizer supporting iterative pair merges on top of byte base."""

    def __init__(self, vocab_size: int = 512) -> None:
        super().__init__(vocab_size=DEFAULT_VOCAB_SIZE)
        self.target_vocab_size = vocab_size
        self.merges: Dict[Tuple[int, int], int] = {}
        self.vocab: Dict[int, bytes] = {
            i + self.byte_offset: bytes([i]) for i in range(256)
        }
        for name, idx in self.special_tokens.items():
            self.vocab[idx] = name.encode("utf-8")

    def train(self, corpus: Union[str, List[str]], target_vocab_size: int) -> None:
        """Trains BPE merges on input corpus up to target_vocab_size."""
        if isinstance(corpus, list):
            corpus = " ".join(corpus)

        ids = [b + self.byte_offset for b in corpus.encode("utf-8")]
        num_merges = target_vocab_size - len(self.vocab)
        curr_id = max(self.vocab.keys()) + 1

        for _ in range(max(0, num_merges)):
            pair_counts: Dict[Tuple[int, int], int] = {}
            for pair in zip(ids[:-1], ids[1:]):
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
            if not pair_counts:
                break
            best_pair = max(pair_counts, key=pair_counts.get)
            if pair_counts[best_pair] < 2:
                break

            new_ids = []
            i = 0
            while i < len(ids):
                if i < len(ids) - 1 and ids[i] == best_pair[0] and ids[i + 1] == best_pair[1]:
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
        """Encodes text using learned BPE merges."""
        if not text:
            ids: List[int] = []
        else:
            ids = [b + self.byte_offset for b in text.encode("utf-8")]
            while len(ids) >= 2:
                stats = {pair: self.merges[pair] for pair in zip(ids[:-1], ids[1:]) if pair in self.merges}
                if not stats:
                    break
                best_pair = min(stats, key=stats.get)
                idx = self.merges[best_pair]
                new_ids = []
                i = 0
                while i < len(ids):
                    if i < len(ids) - 1 and ids[i] == best_pair[0] and ids[i + 1] == best_pair[1]:
                        new_ids.append(idx)
                        i += 2
                    else:
                        new_ids.append(ids[i])
                        i += 1
                ids = new_ids

        if add_bos:
            ids = [self.bos_id] + ids
        if add_eos:
            ids = ids + [self.eos_id]

        return ids

    def decode(self, tokens: List[int], skip_special_tokens: bool = True) -> str:
        """Decodes BPE tokens back to Unicode string."""
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
        """Inspects BPE tokenized text."""
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

        tokens: List[str] = []
        byte_lengths: List[int] = []
        offsets: List[List[int]] = []
        curr_offset = 0

        for t in token_ids:
            chunk = self.vocab.get(t, b"")
            byte_lengths.append(len(chunk))
            try:
                decoded_piece = chunk.decode("utf-8")
            except UnicodeDecodeError:
                decoded_piece = repr(chunk)
            tokens.append(decoded_piece)

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
