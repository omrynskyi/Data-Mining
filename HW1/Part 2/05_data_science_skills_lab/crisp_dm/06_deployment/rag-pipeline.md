---
skill: rag-pipeline
pack: param087/agent-ml-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - src/p6_rag.py
  - artifacts/rag_index/pipeline.pkl
  - artifacts/rag_corpus_manifest.json
  - artifacts/rag_eval.json
  - artifacts/rag_eval.md
---

# RAG Pipeline — "Ask the Project" Retriever over This Lab's Own Docs

## What the skill prescribes

`.claude/skills/rag-pipeline/SKILL.md`: retrieval quality dominates
generation quality, so optimize retrieval first. Pipeline stages: ingest &
chunk (structural boundaries preferred over fixed char counts, ~500-1000
tokens, 10-15% overlap, metadata kept per chunk for citations); embed into a
vector store (cosine similarity); **hybrid retrieval** — dense (semantic) +
sparse (BM25 keyword) unioned, then a **cross-encoder reranked** to the final
top-k, called out as "the biggest quality lever"; prompt assembly restricted
to the top-k reranked chunks with required inline citations; evaluation on
**both halves** — retrieval (recall@k, MRR, hit-rate on a labeled
query→chunk set) and answer quality — via a fixed eval set. Explicit
pitfalls: dense-only retrieval misses exact keywords/IDs, no reranker means
low-precision context, no retrieval eval means tuning blind.

## Applied to Telco churn

No network access and no GPU in this environment rules out downloading an
embedding model or a cross-encoder checkpoint. Per the deployment brief, the
pipeline substitutes offline-available primitives while keeping the same
two-leg hybrid architecture the skill prescribes:

- **"Dense" leg** = `TfidfVectorizer` (1-2 grams, sublinear TF) +
  `sklearn.neighbors.NearestNeighbors` (cosine). This is a real limitation
  worth stating plainly: TF-IDF is a lexical/sparse representation, not a
  learned dense embedding, so it does not capture synonymy the way a real
  embedding model would (e.g. it won't connect "attrition" to "churn" unless
  both literally co-occur enough in the corpus). It plays the dense role
  structurally (a single global vector per chunk, cosine-ranked) while being
  honest about not being semantic in the embedding-model sense.
- **Sparse leg** = Okapi BM25, implemented directly in `src/p6_rag.py`
  (`class BM25`, k1=1.5, b=0.75, IDF with the standard +0.5/+0.5 smoothing)
  — no `rank_bm25` or Elasticsearch dependency.
- **Hybrid fusion** = Reciprocal Rank Fusion (`rrf_fuse`, k_rrf=60) over the
  two rankings' top-20 each, per-retriever.
- **Reranker** = cross-encoder-free by necessity: `lexical_rerank` rescores
  the fused top-20 by the fraction of *distinctive* (IDF-weighted) query
  terms each chunk covers, blended 85/15 with the RRF score as a tie-break.
  This is a real, coded reranking step — not a no-op — but it is a lexical
  reranker, not a learned cross-encoder; called out explicitly here rather
  than left implicit.

### Chunking

The skill's default (~500-1000 tokens / 10-15% overlap) is written for
long, loosely-structured documents. This corpus is the opposite: ~40 short
(avg ~750 words), topic-dense CRISP-DM writeups with real markdown heading
structure, where many eval-relevant facts are single numbers (a SHA-256
hash, a silhouette score) that a 1000-token chunk would dilute by burying
them alongside 3-4 unrelated paragraphs. So chunking here is **structural
first, sized down from the default, and deliberately justified as a
deviation**:

- **Markdown docs:** split on heading boundaries (`#`-`######`) first, so
  a chunk never crosses a section the author intended as one topic. A
  section over ~220 words is then sliding-windowed at 220 words / 33-word
  overlap (~15%, matching the skill's overlap ratio, just at a smaller base
  window sized to this corpus).
- **`semantic_model_telco.yml`:** has no markdown headers, so it gets a
  YAML-specific structural chunker (`chunk_yaml`) that splits on
  `- name: ...` list-item boundaries instead — each dimension, measure, or
  metric definition becomes one semantically complete chunk (e.g. the whole
  `ltv` metric block, including its `calculation_notes`, stays together).
  This follows the skill's "prefer semantic/structural boundaries" rule for
  a file shape the skill's own generic guidance doesn't directly address.
- Every chunk retains `source` (relative file path), `doc_title` (skill
  name from frontmatter), and `heading` metadata for citation, per the
  skill's requirement to keep chunk metadata for citations and filtering.

Result: **268 chunks from 40 source documents** (25 `crisp_dm/**/*.md` docs
at kickoff, growing to ~34 as concurrent Phase 1-5 agents finished writing,
plus `artifacts/data_catalog_telco.md` and `artifacts/semantic_model_telco.yml`)
— see `artifacts/rag_corpus_manifest.json` for the full file list actually
indexed.

### Evaluation — real numbers, not cherry-picked

12 question → expected-source-doc pairs, hand-written from documents
actually read in this session (listed in `EVAL_SET` in `src/p6_rag.py`),
covering every CRISP-DM phase 1-6 and both file types (markdown + YAML). A
hit is doc-level: the retrieved chunk's `source` equals the expected file.

| Retriever | MRR | Hit-rate@1 | Recall@3 | Recall@5 |
|---|---|---|---|---|
| **sparse (BM25)** | **0.7361** | 0.6667 | **0.8333** | 0.8333 |
| dense (TF-IDF+kNN) | 0.6694 | 0.5833 | 0.75 | 0.8333 |
| hybrid (RRF+rerank) | 0.7111 | 0.6667 | 0.75 | 0.8333 |

**Hybrid did not win.** BM25 alone had the best MRR and Recall@3. This is
reported honestly rather than adjusted to make hybrid look good. Two
plausible, checked reasons:

1. **This corpus rewards exact term matching more than semantic
   similarity.** Every question targets specific project vocabulary
   (`silhouette`, `SHA-256`, `Optuna`, `TPESampler`) that appears verbatim
   in the source doc — exactly the regime where BM25's exact-term IDF
   weighting has an edge and a synonym-blind "dense" leg (TF-IDF, not a real
   embedding) adds noise rather than recall. A genuine embedding model would
   likely change this conclusion; it was not available here.
2. **Cross-document redundancy in this specific corpus.** Two of the twelve
   questions (segmentation silhouette scores, dataset grain/row-count)
   missed the top-5 entirely under every retriever — verified directly:
   the true source (`segmentation-analysis.md`) ranked **6th** for the
   silhouette question and `data_catalog_telco.md` ranked **8th** for the
   grain question. Both facts are genuinely repeated, in very similar
   phrasing, across several other Phase 1-6 docs written by concurrently
   running agents in this same project (e.g. `insight-synthesis.md`,
   `analysis-assumptions-log.md`, `methodology-explainer.md` all restate
   "k=3 chosen over k=2's higher silhouette 0.3369 vs 0.3075"). The
   retriever isn't wrong to surface those — they answer the question
   correctly too — but it means the single "expected_doc" ground truth used
   here slightly understates real-world usefulness for a corpus this
   redundant. Full per-question ranks are in `artifacts/rag_eval.md`.

The reranker's blend weight (0.85 coverage / 0.15 RRF) was left as the first
value tried rather than tuned against this same 12-question eval set — tuning
against your own test set would make the eval score meaningless as a measure
of generalization.

## Outputs produced

- `src/p6_rag.py` — full pipeline: chunking, BM25, TF-IDF+kNN, RRF fusion,
  lexical reranker, eval harness, and a CLI:
  ```
  python3 src/p6_rag.py --build                 # (re)build the index
  python3 src/p6_rag.py --query "..." --mode hybrid --k 5
  python3 src/p6_rag.py --eval                   # regenerate rag_eval.{json,md}
  ```
- `artifacts/rag_index/pipeline.pkl` — pickled fitted pipeline (BM25 index +
  TF-IDF matrix + NearestNeighbors index + all 268 chunks with metadata)
- `artifacts/rag_corpus_manifest.json` — exact file list and chunk count
  actually indexed, plus the chunking parameters used
- `artifacts/rag_eval.json` / `artifacts/rag_eval.md` — full eval results:
  summary table above plus all 12 per-question ranks for sparse/dense/hybrid
