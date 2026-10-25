"""RAG evaluation harness: measures retrieval hit-rate@k, factual coverage, abstention, and chunk-size trade-offs."""

import asyncio
from dataclasses import dataclass
import time
from typing import Any
import uuid

from app.evaluation.dataset import EVAL_QUESTIONS, SAMPLE_DOCUMENTS, EvalQuestion
from app.providers.base import EmbeddingProvider, get_embedding_provider
from app.services.chunking import chunk_sections
from app.services.extractor import ExtractedSection
from app.services.retrieval import compute_cosine_similarity

ABSTENTION_TEXT = "I don't know based on the provided documents."


@dataclass
class ChunkConfig:
    name: str
    approx_tokens: int
    char_size: int
    char_overlap: int


# Three distinct chunking configurations approximating 200, 500, and 800 tokens (~4 chars per token)
DEFAULT_CONFIGS = [
    ChunkConfig(
        name="Fine-Grained (Small)",
        approx_tokens=200,
        char_size=800,
        char_overlap=100,
    ),
    ChunkConfig(
        name="Balanced (Medium)",
        approx_tokens=500,
        char_size=2000,
        char_overlap=200,
    ),
    ChunkConfig(
        name="Coarse-Grained (Large)",
        approx_tokens=800,
        char_size=3200,
        char_overlap=400,
    ),
]


@dataclass
class EvalResult:
    config_name: str
    approx_tokens: int
    char_size: int
    char_overlap: int
    total_questions: int
    answerable_count: int
    unanswerable_count: int
    hit_rate_at_k: float  # Fraction of answerable questions with source in top-k
    fact_coverage_rate: float  # Fraction where retrieved context contains expected key facts
    abstention_accuracy: float  # Fraction of unanswerable questions correctly rejected
    avg_chunks_per_doc: float
    total_eval_duration_ms: float


class RAGEvaluator:
    """Evaluates retrieval quality and abstention behavior across chunk configurations."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None):
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def _index_synthetic_corpus(
        self,
        config: ChunkConfig,
    ) -> list[dict[str, Any]]:
        """Splits synthetic policy documents using the specified chunk configuration and computes embeddings."""
        corpus_chunks: list[dict[str, Any]] = []

        for doc_key, doc_meta in SAMPLE_DOCUMENTS.items():
            doc_id = uuid.uuid5(uuid.NAMESPACE_DNS, doc_key)
            # Create section from complete document content to evaluate varying chunk sizes
            sections = [
                ExtractedSection(
                    content=doc_meta["content"],
                    page_number=1,
                    section_title=doc_meta["title"],
                    metadata={"doc_key": doc_key, "doc_title": doc_meta["title"]},
                )
            ]

            chunks = chunk_sections(
                sections=sections,
                document_id=doc_id,
                chunk_size=config.char_size,
                chunk_overlap=config.char_overlap,
            )

            texts = [c.content for c in chunks]
            if texts:
                vectors = await self.embedding_provider.embed_documents(texts)
                for c, vec in zip(chunks, vectors):
                    chunk_id = uuid.uuid5(doc_id, f"chunk_{c.chunk_index}")
                    corpus_chunks.append({
                        "chunk_id": chunk_id,
                        "doc_key": doc_key,
                        "doc_title": doc_meta["title"],
                        "section_title": c.section_title,
                        "content": c.content,
                        "embedding": vec,
                    })

        return corpus_chunks

    async def evaluate_configuration(
        self,
        config: ChunkConfig,
        questions: list[EvalQuestion] | None = None,
        top_k: int = 3,
        min_similarity_threshold: float | None = None,
    ) -> EvalResult:
        """Runs the benchmark questions against a specific chunking configuration."""
        from app.providers.base import MockEmbeddingProvider, MockLLMProvider
        from app.services.answering import generate_grounded_answer
        from app.services.retrieval import RetrievedChunk

        eval_questions = questions or EVAL_QUESTIONS
        start_time = time.perf_counter()

        # Calibration: Mock term-hash operates around 0.12-0.35; dense hosted embeddings around 0.45-0.85
        threshold = (
            min_similarity_threshold
            if min_similarity_threshold is not None
            else (0.12 if isinstance(self.embedding_provider, MockEmbeddingProvider) else 0.45)
        )

        # 1. Chunk and embed the evaluation corpus
        corpus_chunks = await self._index_synthetic_corpus(config)
        avg_chunks = round(len(corpus_chunks) / max(1, len(SAMPLE_DOCUMENTS)), 1)

        answerable_questions = [q for q in eval_questions if q.is_answerable]
        unanswerable_questions = [q for q in eval_questions if not q.is_answerable]

        hits = 0
        fact_hits = 0
        abstention_successes = 0

        # 2. Evaluate answerable questions
        for q in answerable_questions:
            q_vec = await self.embedding_provider.embed_query(q.question)
            # Calculate cosine similarities against all chunks
            scored = []
            for c in corpus_chunks:
                sim = compute_cosine_similarity(q_vec, c["embedding"])
                scored.append((sim, c))
            scored.sort(key=lambda x: x[0], reverse=True)

            # Filter top-k by threshold
            top_candidates = [c for sim, c in scored[:top_k] if sim >= threshold]

            # Hit-Rate@k: Is expected document in top-k?
            hit = any(c["doc_key"] == q.expected_doc for c in top_candidates)
            if hit:
                hits += 1

            # Simple Fact Check: Are all expected keywords present across the retrieved text?
            combined_text = " ".join(c["content"].lower() for c in top_candidates)
            has_all_facts = all(f.lower() in combined_text for f in q.expected_facts)
            if has_all_facts:
                fact_hits += 1

        # 3. Evaluate unanswerable questions (Testing both retrieval-level and generation-level abstention)
        eval_llm = MockLLMProvider()

        for q in unanswerable_questions:
            q_vec = await self.embedding_provider.embed_query(q.question)
            scored = []
            for c in corpus_chunks:
                sim = compute_cosine_similarity(q_vec, c["embedding"])
                scored.append((sim, c))
            scored.sort(key=lambda x: x[0], reverse=True)

            top_retrieved = [
                RetrievedChunk(
                    chunk_id=c["chunk_id"],
                    document_id=uuid.uuid5(uuid.NAMESPACE_DNS, c["doc_key"]),
                    document_title=c["doc_title"],
                    document_filename=f"{c['doc_key']}.txt",
                    chunk_index=0,
                    page_number=1,
                    section_title=c["section_title"],
                    content=c["content"],
                    similarity_score=sim,
                )
                for sim, c in scored[:top_k]
                if sim >= threshold
            ]

            # Retrieval-level abstention: no chunks meet the similarity threshold
            if not top_retrieved:
                abstention_successes += 1
            else:
                # Generation-level abstention: candidate chunks pass threshold but do not support the query
                ans = await generate_grounded_answer(
                    question=q.question,
                    retrieved_chunks=top_retrieved,
                    llm_provider=eval_llm,
                )
                if ans.is_unanswerable or ans.answer == ABSTENTION_TEXT:
                    abstention_successes += 1

        duration_ms = (time.perf_counter() - start_time) * 1000

        hit_rate = round(hits / max(1, len(answerable_questions)), 4)
        fact_rate = round(fact_hits / max(1, len(answerable_questions)), 4)
        abstain_rate = round(abstention_successes / max(1, len(unanswerable_questions)), 4)

        return EvalResult(
            config_name=config.name,
            approx_tokens=config.approx_tokens,
            char_size=config.char_size,
            char_overlap=config.char_overlap,
            total_questions=len(eval_questions),
            answerable_count=len(answerable_questions),
            unanswerable_count=len(unanswerable_questions),
            hit_rate_at_k=hit_rate,
            fact_coverage_rate=fact_rate,
            abstention_accuracy=abstain_rate,
            avg_chunks_per_doc=avg_chunks,
            total_eval_duration_ms=round(duration_ms, 2),
        )

    async def compare_configurations(
        self,
        configs: list[ChunkConfig] | None = None,
        top_k: int = 3,
    ) -> list[EvalResult]:
        """Runs comparative benchmarks across all provided chunk configurations."""
        target_configs = configs or DEFAULT_CONFIGS
        results: list[EvalResult] = []
        for cfg in target_configs:
            res = await self.evaluate_configuration(cfg, top_k=top_k)
            results.append(res)
        return results


def format_evaluation_table(results: list[EvalResult]) -> str:
    """Formats comparative evaluation results into a clean markdown table."""
    headers = [
        "Configuration",
        "Approx Tokens",
        "Chars (Size/Overlap)",
        "Hit-Rate@3",
        "Fact Coverage",
        "Abstention Acc.",
        "Chunks/Doc",
        "Latency (ms)",
    ]
    rows = []
    for r in results:
        rows.append([
            r.config_name,
            f"~{r.approx_tokens} tokens",
            f"{r.char_size} / {r.char_overlap}",
            f"{r.hit_rate_at_k * 100:.1f}%",
            f"{r.fact_coverage_rate * 100:.1f}%",
            f"{r.abstention_accuracy * 100:.1f}%",
            f"{r.avg_chunks_per_doc}",
            f"{r.total_eval_duration_ms:.0f} ms",
        ])

    col_widths = [max(len(str(val)) for val in [h] + [r[i] for r in rows]) for i, h in enumerate(headers)]

    def make_row(items: list[str]) -> str:
        return "| " + " | ".join(item.ljust(col_widths[i]) for i, item in enumerate(items)) + " |"

    sep_row = "| " + " | ".join("-" * w for w in col_widths) + " |"

    table_lines = [
        make_row(headers),
        sep_row,
    ]
    for row in rows:
        table_lines.append(make_row(row))

    return "\n".join(table_lines)
