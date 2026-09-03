Project 02: Nano LLM Transformer

WHAT IT IS
A small language model built entirely from scratch in pure PyTorch, with no torch.nn.Transformer and no HuggingFace shortcuts. It implements Rotary Position Embeddings, Grouped Query Attention, SwiGLU, and RMSNorm by hand, plus a KV-cache for fast generation.

HOW TO RUN
Command: make 02   (or ./run --02)
Opens at: http://localhost:8002 (admin dashboard)

FILES TO SHOW ON SCREEN
1. nano_transformer/attention.py - the attention mechanism, written from scratch
2. test_model.py - a gradient check suite that proves every layer trains correctly

CODE - nano_transformer/attention.py (forward pass, simplified)

q = self.q_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
k = self.k_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
v = self.v_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)

# Rotary position embeddings, applied directly to q and k
q = self.rope(q, start_pos=start_pos)
k = self.rope(k, start_pos=start_pos)

# Grouped Query Attention: fewer K/V heads than Q heads, expanded back up
k_exp = repeat_kv(k, self.n_rep)
v_exp = repeat_kv(v, self.n_rep)

scale = 1.0 / math.sqrt(self.head_dim)
scores = torch.matmul(q, k_exp.transpose(-2, -1)) * scale

# Causal mask: a token can only attend to itself and earlier tokens
mask = q_pos >= k_pos
scores = scores.masked_fill(~mask, float("-inf"))

attn_weights = F.softmax(scores.float(), dim=-1).type_as(x)
context = torch.matmul(attn_weights, v_exp)

Walk through this in order: project into queries, keys, values, rotate q and k with RoPE, expand the shared key/value heads for GQA, compute scaled dot product attention scores, mask out future tokens, softmax, then combine with the values.

SCRIPT

Intro, 0:00 to 0:25
Say you are showing Project 02, the pure PyTorch nano LLM transformer.
Launch it with make 02.
Mention this starts the FastAPI admin dashboard on localhost port 8002.

Code walkthrough, 0:25 to 1:25
Open nano_transformer/attention.py.
Explain that every primitive here, attention, RoPE, GQA, KV-cache, is hand written instead of using a library wrapper.
Walk through the forward pass: project q, k, v, rotate q and k with RoPE for position information, expand the grouped key/value heads back up to match the query heads, apply the causal mask so tokens cannot see the future, then softmax and combine with values.
Open test_model.py and mention this file runs a gradient check confirming every layer, including RoPE, SwiGLU, and RMSNorm, actually receives and passes gradients correctly during training.

Live demo, 1:25 to 2:10
Switch to the browser at localhost 8002.
Show the model architecture panel, training metrics, and hardware memory stats.
Submit a text prompt and show the model generating text token by token using the KV-cache.

Wrap up
This concludes Project 02.
