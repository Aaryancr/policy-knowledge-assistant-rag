"""Unit tests for the RAG evaluation dataset, metric calculations, and harness."""

import pytest

from app.evaluation.dataset import EVAL_QUESTIONS, SAMPLE_DOCUMENTS, EvalQuestion
from app.evaluation.evaluator import (
    DEFAULT_CONFIGS,
    ChunkConfig,
    EvalResult,
    RAGEvaluator,
    format_evaluation_table,
)
from app.providers.base import MockEmbeddingProvider


def test_eval_dataset_structure_and_counts():
    """Validates the synthetic policy evaluation dataset meets benchmark requirements."""
    # 1. Four synthetic policy documents
    assert len(SAMPLE_DOCUMENTS) == 4
    expected_doc_keys = {
        "remote_work_policy",
        "leave_and_time_off_policy",
        "it_security_and_device_policy",
        "travel_and_expense_policy",
    }
    assert set(SAMPLE_DOCUMENTS.keys()) == expected_doc_keys

    for doc_key, meta in SAMPLE_DOCUMENTS.items():
        assert "title" in meta
        assert "content" in meta
        assert len(meta["content"].strip()) > 200

    # 2. Between 25 and 30 questions
    assert 25 <= len(EVAL_QUESTIONS) <= 30
    assert len(EVAL_QUESTIONS) == 28

    answerable = [q for q in EVAL_QUESTIONS if q.is_answerable]
    unanswerable = [q for q in EVAL_QUESTIONS if not q.is_answerable]
    cross_section = [q for q in EVAL_QUESTIONS if q.question_type == "cross_section"]
    distractor = [q for q in EVAL_QUESTIONS if q.question_type == "distractor"]

    # At least 20 answerable, at least 4 unanswerable, cross-section and distractor present
    assert len(answerable) >= 20
    assert len(unanswerable) >= 4
    assert len(cross_section) >= 3
    assert len(distractor) >= 3

    for q in answerable:
        assert q.expected_doc in expected_doc_keys
        assert len(q.expected_facts) > 0


def test_chunk_configurations_character_to_token_approximation():
    """Verifies at least 3 distinct chunk configurations approximating 200, 500, and 800 tokens."""
    assert len(DEFAULT_CONFIGS) >= 3
    approx_tokens = [cfg.approx_tokens for cfg in DEFAULT_CONFIGS]
    assert 200 in approx_tokens
    assert 500 in approx_tokens
    assert 800 in approx_tokens

    for cfg in DEFAULT_CONFIGS:
        # Check character to token approximation is roughly 4:1
        ratio = cfg.char_size / cfg.approx_tokens
        assert 3.5 <= ratio <= 4.5
        assert cfg.char_overlap < cfg.char_size
        assert cfg.char_overlap > 0


async def test_evaluator_indexes_synthetic_corpus():
    """Verifies evaluator indexes synthetic documents into chunks with embeddings."""
    evaluator = RAGEvaluator(embedding_provider=MockEmbeddingProvider())
    cfg = DEFAULT_CONFIGS[0]
    chunks = await evaluator._index_synthetic_corpus(cfg)

    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert "chunk_id" in first_chunk
    assert "doc_key" in first_chunk
    assert "content" in first_chunk
    assert "embedding" in first_chunk
    assert len(first_chunk["embedding"]) == 1536


async def test_evaluator_metric_computations_and_unanswerable_abstention():
    """Verifies hit-rate@k, fact coverage, and abstention calculation logic."""
    evaluator = RAGEvaluator(embedding_provider=MockEmbeddingProvider())

    test_cfg = ChunkConfig(
        name="Test Config",
        approx_tokens=500,
        char_size=2000,
        char_overlap=200,
    )

    # Run on a subset of 2 answerable + 2 unanswerable questions
    subset_questions = [
        EVAL_QUESTIONS[0],  # Q01: password length (answerable)
        EVAL_QUESTIONS[1],  # Q02: PTO days (answerable)
        EVAL_QUESTIONS[23], # Q24: pet insurance (unanswerable)
        EVAL_QUESTIONS[24], # Q25: dogs in office (unanswerable)
    ]

    result = await evaluator.evaluate_configuration(
        config=test_cfg,
        questions=subset_questions,
        top_k=3,
        min_similarity_threshold=0.1,
    )

    assert result.total_questions == 4
    assert result.answerable_count == 2
    assert result.unanswerable_count == 2
    assert 0.0 <= result.hit_rate_at_k <= 1.0
    assert 0.0 <= result.fact_coverage_rate <= 1.0
    assert 0.0 <= result.abstention_accuracy <= 1.0
    assert result.total_eval_duration_ms > 0


def test_format_evaluation_table():
    """Verifies formatting of the comparative results markdown table."""
    sample_results = [
        EvalResult(
            config_name="Fine-Grained (Small)",
            approx_tokens=200,
            char_size=800,
            char_overlap=100,
            total_questions=28,
            answerable_count=23,
            unanswerable_count=5,
            hit_rate_at_k=0.913,
            fact_coverage_rate=0.870,
            abstention_accuracy=1.0,
            avg_chunks_per_doc=4.2,
            total_eval_duration_ms=45.2,
        ),
        EvalResult(
            config_name="Balanced (Medium)",
            approx_tokens=500,
            char_size=2000,
            char_overlap=200,
            total_questions=28,
            answerable_count=23,
            unanswerable_count=5,
            hit_rate_at_k=0.957,
            fact_coverage_rate=0.913,
            abstention_accuracy=1.0,
            avg_chunks_per_doc=2.1,
            total_eval_duration_ms=42.1,
        ),
    ]

    table_md = format_evaluation_table(sample_results)
    assert "| Configuration" in table_md
    assert "| Hit-Rate@3" in table_md
    assert "| Fine-Grained (Small)" in table_md
    assert "| Balanced (Medium)" in table_md
    assert "95.7%" in table_md
