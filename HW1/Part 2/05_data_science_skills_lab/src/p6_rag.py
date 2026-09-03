"""
p6_rag.py — CRISP-DM Phase 6 (Deployment): rag-pipeline skill.

A real, working, evaluated "ask the project" retriever over this lab's own
CRISP-DM documentation. No network, no GPU, per environment constraints:

  - "Dense" retrieval  = TfidfVectorizer + sklearn NearestNeighbors (cosine).
    No embedding model is reachable offline, so TF-IDF+kNN stands in as the
    dense-ish leg of the pipeline (this is a real limitation, called out in
    the doc — TF-IDF is technically a lexical/sparse representation, not a
    learned dense embedding, but it plays the "dense" role in this hybrid
    per the deployment brief).
  - "Sparse" retrieval = BM25 (Okapi), implemented directly below, no library.
  - Hybrid              = Reciprocal Rank Fusion (RRF) over the two rankings.
  - Reranker            = cross-encoder-free: a lexical query-coverage
    reranker (fraction of unique query terms present in the chunk, weighted
    by each term's corpus IDF) applied to the fused top-N.

Usage:
    python3 src/p6_rag.py --build            # build indices, save to artifacts/rag_index/
    python3 src/p6_rag.py --query "..."       # query the CLI
    python3 src/p6_rag.py --eval              # run the eval set, write rag_eval.{json,md}
"""
import argparse
import json
import math
import pickle
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

ROOT = Path("/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/05_data_science_skills_lab")
ART = ROOT / "artifacts"
INDEX_DIR = ART / "rag_index"

# ---------------------------------------------------------------------------
# 1. Ingest & chunk
# ---------------------------------------------------------------------------
# Chunking strategy (deviates from the skill's generic ~500-1000 token
# default, deliberately, and says so): this corpus is ~35 short, topic-dense
# markdown docs (avg ~750 words) plus one YAML semantic model. Sections are
# already short (a "## Applied to Telco churn" section is often 150-400
# words) and many eval-relevant facts are single numbers (a SHA-256 hash, a
# silhouette score) that a large chunk would dilute with unrelated
# neighboring content. So: split on structural boundaries first (markdown
# headings; YAML list-item boundaries), and only fall back to a sliding
# window when a section still exceeds ~220 words, using a 15% overlap
# (~30 words) so a fact near a chunk edge isn't stranded outside every chunk.
TARGET_WORDS = 220
OVERLAP_WORDS = 33  # ~15% of 220, matches skill's "10-15% overlap" guidance

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def _parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), text[m.end():]
    meta = {}
    for line in fm_text.splitlines():
        if ":" in line and not line.strip().startswith("-"):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def _split_words(text, target=TARGET_WORDS, overlap=OVERLAP_WORDS):
    words = text.split()
    if len(words) <= target:
        return [text.strip()] if text.strip() else []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + target, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def chunk_markdown(path):
    """Structural chunking: split on headings, then sliding-window any
    section that's still too long."""
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    doc_title = meta.get("skill", path.stem)

    heads = list(HEADING_RE.finditer(body))
    sections = []
    if not heads:
        sections.append(("", body))
    else:
        # preamble before first heading (if any)
        if heads[0].start() > 0:
            pre = body[: heads[0].start()].strip()
            if pre:
                sections.append(("", pre))
        for i, h in enumerate(heads):
            heading_text = h.group(2).strip()
            start = h.end()
            end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
            sections.append((heading_text, body[start:end].strip()))

    chunks = []
    for heading, sec_text in sections:
        if not sec_text:
            continue
        for j, piece in enumerate(_split_words(sec_text)):
            chunks.append({
                "text": (f"{heading}: {piece}" if heading else piece),
                "source": str(path.relative_to(ROOT)),
                "doc_title": doc_title,
                "heading": heading,
                "part": j,
            })
    return chunks


def chunk_yaml(path):
    """YAML-specific structural chunking: split on list-item boundaries
    (`  - name: ...`) rather than generic headings, since dbt-style
    semantic-model YAML has no markdown headers but a clear repeating
    structure (each dimension/measure/metric is one semantically complete
    unit)."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    item_re = re.compile(r"^\s*-\s*name:\s*(\S.*)$")
    top_key_re = re.compile(r"^(\w[\w_]*):\s*$")

    blocks = []
    current_lines = []
    current_name = None
    current_top = None
    top_key = None

    def flush():
        if current_lines:
            blocks.append((current_top, current_name, "\n".join(current_lines)))

    for line in lines:
        tk = top_key_re.match(line)
        if tk and not line.startswith(" "):
            top_key = tk.group(1)
        im = item_re.match(line)
        if im and len(line) - len(line.lstrip()) <= 4:
            flush()
            current_lines = [line]
            current_name = im.group(1).strip()
            current_top = top_key
        else:
            current_lines.append(line)
    flush()

    chunks = []
    for top, name, text in blocks:
        text = text.strip()
        if not text:
            continue
        heading = f"{top}.{name}" if top and name else (top or name or "")
        for j, piece in enumerate(_split_words(text, target=260, overlap=40)):
            chunks.append({
                "text": f"{heading}: {piece}" if heading else piece,
                "source": str(path.relative_to(ROOT)),
                "doc_title": path.stem,
                "heading": heading,
                "part": j,
            })
    return chunks


def build_corpus():
    md_paths = sorted((ROOT / "crisp_dm").rglob("*.md"))
    extra_md = [ART / "data_catalog_telco.md"]
    yaml_paths = [ART / "semantic_model_telco.yml"]

    all_chunks = []
    for p in md_paths + extra_md:
        if p.exists():
            all_chunks.extend(chunk_markdown(p))
    for p in yaml_paths:
        if p.exists():
            all_chunks.extend(chunk_yaml(p))

    for i, c in enumerate(all_chunks):
        c["chunk_id"] = i
    return all_chunks


# ---------------------------------------------------------------------------
# 2. Tokenizer shared by BM25 and reported stats
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_\-]*")


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


# ---------------------------------------------------------------------------
# 3. BM25 (Okapi), implemented directly — no rank_bm25 / whoosh dependency
# ---------------------------------------------------------------------------
class BM25:
    def __init__(self, docs_tokens, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs_tokens = docs_tokens
        self.N = len(docs_tokens)
        self.doc_lens = np.array([len(d) for d in docs_tokens])
        self.avgdl = self.doc_lens.mean() if self.N else 0.0
        self.df = Counter()
        for toks in docs_tokens:
            for t in set(toks):
                self.df[t] += 1
        self.idf = {
            t: math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for t, df in self.df.items()
        }
        self.tf = [Counter(toks) for toks in docs_tokens]

    def score(self, query_tokens, doc_idx):
        tf = self.tf[doc_idx]
        dl = self.doc_lens[doc_idx]
        s = 0.0
        for t in query_tokens:
            if t not in tf:
                continue
            idf = self.idf.get(t, 0.0)
            f = tf[t]
            denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            s += idf * (f * (self.k1 + 1)) / (denom or 1e-9)
        return s

    def search(self, query, k=10):
        q_toks = tokenize(query)
        scores = np.array([self.score(q_toks, i) for i in range(self.N)])
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]


# ---------------------------------------------------------------------------
# 4. "Dense-ish": TF-IDF + NearestNeighbors (cosine)
# ---------------------------------------------------------------------------
class DenseIndex:
    def __init__(self, texts):
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenize, lowercase=False, token_pattern=None,
            sublinear_tf=True, ngram_range=(1, 2), min_df=1, max_df=0.9)
        self.matrix = self.vectorizer.fit_transform(texts)
        self.nn = NearestNeighbors(metric="cosine", algorithm="brute")
        self.nn.fit(self.matrix)

    def search(self, query, k=10):
        qv = self.vectorizer.transform([query])
        n = min(k, self.matrix.shape[0])
        dist, idx = self.nn.kneighbors(qv, n_neighbors=n)
        sims = 1 - dist[0]
        return [(int(i), float(s)) for i, s in zip(idx[0], sims) if s > 0]


# ---------------------------------------------------------------------------
# 5. Hybrid fusion (Reciprocal Rank Fusion) + lexical reranker
# ---------------------------------------------------------------------------
def rrf_fuse(rankings, k_rrf=60, top_k=10):
    """rankings: list of ranked (doc_idx, score) lists. RRF score = sum of
    1/(k_rrf + rank) across the rankings a doc appears in (rank is 1-based)."""
    fused = Counter()
    for ranking in rankings:
        for rank, (idx, _score) in enumerate(ranking, start=1):
            fused[idx] += 1.0 / (k_rrf + rank)
    return sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]


def lexical_rerank(query, candidates, chunks, idf_lookup, top_k=5):
    """Cross-encoder-free reranker: rescore fused candidates by the fraction
    of unique query terms present in the chunk, weighted by each matched
    term's corpus IDF (favors chunks that cover more of the *distinctive*
    query vocabulary, not just any overlap)."""
    q_toks = set(tokenize(query))
    if not q_toks:
        return candidates[:top_k]
    max_possible = sum(idf_lookup.get(t, 0.0) for t in q_toks) or 1.0
    rescored = []
    for idx, fused_score in candidates:
        toks = set(tokenize(chunks[idx]["text"]))
        matched = q_toks & toks
        coverage = sum(idf_lookup.get(t, 0.0) for t in matched) / max_possible
        # blend: mostly the coverage signal, small tie-break from fused RRF score
        rescored.append((idx, 0.85 * coverage + 0.15 * fused_score))
    rescored.sort(key=lambda kv: -kv[1])
    return rescored[:top_k]


# ---------------------------------------------------------------------------
# 6. Pipeline object
# ---------------------------------------------------------------------------
class RagPipeline:
    def __init__(self, chunks):
        self.chunks = chunks
        self.texts = [c["text"] for c in chunks]
        self.tokens = [tokenize(t) for t in self.texts]
        self.bm25 = BM25(self.tokens)
        self.dense = DenseIndex(self.texts)

    def search_sparse(self, query, k=10):
        return self.bm25.search(query, k=k)

    def search_dense(self, query, k=10):
        return self.dense.search(query, k=k)

    def search_hybrid(self, query, k=10, rerank=True):
        sparse = self.search_sparse(query, k=20)
        dense = self.search_dense(query, k=20)
        fused = rrf_fuse([sparse, dense], top_k=20)
        if not rerank:
            return fused[:k]
        return lexical_rerank(query, fused, self.chunks, self.bm25.idf, top_k=k)

    def answer(self, query, k=5, mode="hybrid"):
        if mode == "sparse":
            hits = self.search_sparse(query, k=k)
        elif mode == "dense":
            hits = self.search_dense(query, k=k)
        else:
            hits = self.search_hybrid(query, k=k)
        results = []
        for idx, score in hits:
            c = self.chunks[idx]
            results.append({
                "score": round(score, 4),
                "source": c["source"],
                "heading": c["heading"],
                "text": c["text"][:400],
            })
        return results

    def save(self, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "pipeline.pkl", "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(out_dir):
        with open(out_dir / "pipeline.pkl", "rb") as f:
            return pickle.load(f)


# ---------------------------------------------------------------------------
# 7. Evaluation: 12 hand-written question -> expected-source-doc pairs
# ---------------------------------------------------------------------------
# Every question below was written after actually reading the cited doc in
# this conversation (not generated from the question alone), per the
# deployment brief. Ground truth is doc-level (a chunk "hits" if its
# `source` field equals expected_doc) since a document, not one specific
# chunk boundary, is the unit a human would cite.
EVAL_SET = [
    {"q": "What silhouette score did the k=3 customer segmentation achieve, and why was it chosen over k=2 which scored higher?",
     "expected_doc": "crisp_dm/03_data_preparation/segmentation-analysis.md"},
    {"q": "Which step of the service-adoption funnel has the biggest absolute drop-off in customers?",
     "expected_doc": "crisp_dm/03_data_preparation/funnel-analysis.md"},
    {"q": "What SHA-256 hash is the raw Telco CSV pinned to for reproducibility checks?",
     "expected_doc": "crisp_dm/04_modeling/reproducible-ml.md"},
    {"q": "Which class-imbalance strategy was the cheapest leak-free first move and how did its recall compare to the baseline?",
     "expected_doc": "crisp_dm/04_modeling/imbalanced-data.md"},
    {"q": "What business rule links TotalCharges being null to the tenure column in the data quality audit?",
     "expected_doc": "crisp_dm/02_data_understanding/data-quality-audit.md"},
    {"q": "How many tables does the reverse-engineered normalized schema for the Telco data have, and was it inferred or given by a real database?",
     "expected_doc": "crisp_dm/02_data_understanding/schema-mapper.md"},
    {"q": "What Optuna sampler was used for hyperparameter tuning and what metric did it optimize across which cross-validation folds?",
     "expected_doc": "crisp_dm/04_modeling/hyperparameter-tuning.md"},
    {"q": "Who is the primary audience for the retention risk dashboard and what one-sentence question must it answer?",
     "expected_doc": "crisp_dm/06_deployment/dashboard-specification.md"},
    {"q": "How is the ltv metric defined in the semantic model, and why can't LTV:CAC be computed for this dataset?",
     "expected_doc": "artifacts/semantic_model_telco.yml"},
    {"q": "What was the root business question the VP of Customer Retention actually needed, surfaced via the five-whys technique?",
     "expected_doc": "crisp_dm/01_business_understanding/stakeholder-requirements-gathering.md"},
    {"q": "What two problems does the chart selection guidance say a 3D pie chart and a dual y-axis chart create?",
     "expected_doc": "crisp_dm/06_deployment/visualization-builder.md"},
    {"q": "What is the grain of the Telco-Customer-Churn dataset and how many rows and columns does it have?",
     "expected_doc": "artifacts/data_catalog_telco.md"},
]


def evaluate(pipe, k_values=(1, 3, 5)):
    modes = ["sparse", "dense", "hybrid"]
    per_mode = {m: {"ranks": [], "hits_at": {k: 0 for k in k_values}} for m in modes}

    max_k = max(k_values)
    detail_rows = []
    for item in EVAL_SET:
        q, expected = item["q"], item["expected_doc"]
        row = {"question": q, "expected_doc": expected}
        for mode in modes:
            if mode == "sparse":
                hits = pipe.search_sparse(q, k=max_k)
            elif mode == "dense":
                hits = pipe.search_dense(q, k=max_k)
            else:
                hits = pipe.search_hybrid(q, k=max_k)
            sources = [pipe.chunks[idx]["source"] for idx, _ in hits]
            rank = next((i + 1 for i, s in enumerate(sources) if s == expected), None)
            per_mode[mode]["ranks"].append(rank)
            for k in k_values:
                if rank is not None and rank <= k:
                    per_mode[mode]["hits_at"][k] += 1
            row[f"{mode}_rank"] = rank
            row[f"{mode}_top1_source"] = sources[0] if sources else None
        detail_rows.append(row)

    n = len(EVAL_SET)
    summary = {}
    for mode in modes:
        ranks = per_mode[mode]["ranks"]
        mrr = sum(1.0 / r for r in ranks if r is not None) / n
        summary[mode] = {
            "n_questions": n,
            "mrr": round(mrr, 4),
            "hit_rate_at_1": round(per_mode[mode]["hits_at"][1] / n, 4),
            "recall_at_3": round(per_mode[mode]["hits_at"][3] / n, 4),
            "recall_at_5": round(per_mode[mode]["hits_at"][5] / n, 4),
        }
    return summary, detail_rows


def write_eval_report(summary, detail_rows):
    out_json = {"summary": summary, "detail": detail_rows}
    (ART / "rag_eval.json").write_text(json.dumps(out_json, indent=2))

    lines = ["# RAG Retrieval Evaluation — Telco Churn Project Docs\n",
             "Hand-written eval set: 12 question -> expected-source-doc pairs, ",
             "written from documents actually read in this session. A hit is ",
             "doc-level: the retrieved chunk's source file equals the expected doc.\n",
             "## Summary\n",
             "| Retriever | MRR | Hit-rate@1 | Recall@3 | Recall@5 |",
             "|---|---|---|---|---|"]
    for mode in ["sparse", "dense", "hybrid"]:
        s = summary[mode]
        lines.append(f"| {mode} | {s['mrr']} | {s['hit_rate_at_1']} | {s['recall_at_3']} | {s['recall_at_5']} |")

    best = max(summary, key=lambda m: summary[m]["mrr"])
    lines.append(f"\n**Best by MRR: {best}** ({summary[best]['mrr']})\n")

    lines.append("## Per-question detail\n")
    lines.append("| # | Question | Expected doc | sparse rank | dense rank | hybrid rank |")
    lines.append("|---|---|---|---|---|---|")
    for i, row in enumerate(detail_rows, start=1):
        q_short = row["question"][:70] + ("…" if len(row["question"]) > 70 else "")
        lines.append(f"| {i} | {q_short} | `{row['expected_doc']}` | "
                      f"{row['sparse_rank']} | {row['dense_rank']} | {row['hybrid_rank']} |")

    (ART / "rag_eval.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--query", type=str, default=None)
    ap.add_argument("--mode", choices=["sparse", "dense", "hybrid"], default="hybrid")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--eval", action="store_true")
    args = ap.parse_args()

    if args.build or (not INDEX_DIR.exists() and (args.query or args.eval)):
        t0 = time.time()
        chunks = build_corpus()
        print(f"Built {len(chunks)} chunks from corpus in {time.time()-t0:.2f}s")
        pipe = RagPipeline(chunks)
        pipe.save(INDEX_DIR)
        print(f"Saved index to {INDEX_DIR}")
        with open(ART / "rag_corpus_manifest.json", "w") as f:
            docs = sorted(set(c["source"] for c in chunks))
            json.dump({
                "n_chunks": len(chunks),
                "n_source_docs": len(docs),
                "source_docs": docs,
                "chunking": {
                    "strategy": "structural (markdown heading / YAML list-item boundaries) "
                                "+ sliding-window fallback for oversized sections",
                    "target_words": TARGET_WORDS,
                    "overlap_words": OVERLAP_WORDS,
                },
            }, f, indent=2)
    else:
        pipe = RagPipeline.load(INDEX_DIR) if INDEX_DIR.exists() else None

    if args.query:
        if pipe is None:
            chunks = build_corpus()
            pipe = RagPipeline(chunks)
        results = pipe.answer(args.query, k=args.k, mode=args.mode)
        print(f"\nQuery ({args.mode}): {args.query}\n")
        for r in results:
            print(f"[{r['score']}] {r['source']}  ({r['heading']})")
            print(f"    {r['text']}\n")

    if args.eval:
        if pipe is None:
            chunks = build_corpus()
            pipe = RagPipeline(chunks)
        summary, detail = evaluate(pipe)
        write_eval_report(summary, detail)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
