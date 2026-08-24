from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from bimbam_agent.models import Chunk
from bimbam_agent.retrieval import HybridRetriever


class FakeEmbeddingProvider:
    """Provedor previsível e totalmente offline usado pelos testes."""

    def __init__(
        self,
        document_vectors: Sequence[Sequence[float]],
        query_vector: Sequence[float],
        *,
        fail_documents: bool = False,
        fail_query: bool = False,
    ) -> None:
        self.document_vectors = document_vectors
        self.query_vector = query_vector
        self.fail_documents = fail_documents
        self.fail_query = fail_query
        self.document_calls = 0
        self.query_calls = 0

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.document_calls += 1
        if self.fail_documents:
            raise RuntimeError("falha simulada ao indexar")
        assert len(texts) == len(self.document_vectors)
        return self.document_vectors

    def embed_query(self, text: str) -> Sequence[float]:
        self.query_calls += 1
        if self.fail_query:
            raise RuntimeError("falha simulada na consulta")
        return self.query_vector


def make_chunk(chunk_id: str, text: str, *, source: str = "FAQ.pdf") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_name=source,
        source_path=Path("data/documents") / source,
        location=f"seção-{chunk_id}",
    )


def test_lexical_search_is_available_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    chunks = [
        make_chunk("envio", "O prazo de envio e rastreamento da compra."),
        make_chunk("pix", "O pagamento por Pix tem confirmação rápida."),
        make_chunk("garantia", "A garantia cobre defeitos de fabricação."),
    ]

    retriever = HybridRetriever(chunks, top_k=2, min_score=0.0)
    results = retriever.search("Como funciona o pagamento via Pix?")

    assert retriever.lexical_available
    assert not retriever.semantic_available
    assert results[0].chunk.chunk_id == "pix"
    assert results[0].score == pytest.approx(1.0)
    assert results[0].lexical_score == pytest.approx(1.0)
    assert results[0].semantic_score == 0.0
    assert all(0.0 <= result.score <= 1.0 for result in results)


def test_hybrid_search_combines_normalized_scores() -> None:
    chunks = [
        make_chunk("lexical", "reembolso reembolso devolução"),
        make_chunk("semantic", "estorno de uma compra aprovada"),
    ]
    provider = FakeEmbeddingProvider(
        document_vectors=[[0.0, 1.0], [1.0, 0.0]],
        query_vector=[1.0, 0.0],
    )
    retriever = HybridRetriever(
        chunks,
        embedding_provider=provider,
        semantic_weight=0.8,
        lexical_weight=0.2,
        top_k=2,
        min_score=0.0,
    )

    results = retriever.search("reembolso")

    assert provider.document_calls == 1
    assert provider.query_calls == 1
    assert retriever.semantic_available
    assert [result.chunk.chunk_id for result in results] == ["semantic", "lexical"]
    assert results[0].semantic_score == pytest.approx(1.0)
    assert results[0].lexical_score == 0.0
    assert results[0].score == pytest.approx(0.8)
    assert results[1].score == pytest.approx(0.2)


@pytest.mark.parametrize("failure_stage", ["documents", "query"])
def test_embedding_error_falls_back_to_lexical(failure_stage: str) -> None:
    chunks = [
        make_chunk("afiliados", "Comissão do programa de afiliados."),
        make_chunk("entrega", "Prazo estimado para entrega do pedido."),
    ]
    provider = FakeEmbeddingProvider(
        document_vectors=[[1.0, 0.0], [0.0, 1.0]],
        query_vector=[1.0, 0.0],
        fail_documents=failure_stage == "documents",
        fail_query=failure_stage == "query",
    )
    retriever = HybridRetriever(
        chunks,
        embedding_provider=provider,
        top_k=1,
        min_score=0.0,
    )

    results = retriever.search("qual o prazo de entrega?")

    assert [result.chunk.chunk_id for result in results] == ["entrega"]
    assert results[0].score == pytest.approx(1.0)
    assert results[0].semantic_score == 0.0
    assert retriever.semantic_error is not None
    assert "RuntimeError" in retriever.semantic_error


def test_top_k_min_score_deduplication_and_tie_break_are_deterministic() -> None:
    chunks = [
        make_chunk("b", "garantia estendida"),
        make_chunk("a", "garantia estendida"),
        make_chunk("c", "garantia legal"),
        make_chunk("d", "pagamento com cartão"),
    ]
    retriever = HybridRetriever(
        chunks,
        auto_embeddings=False,
        top_k=3,
        min_score=0.0,
    )

    results = retriever.search("garantia", top_k=2, min_score=0.5)

    # Os textos repetidos aparecem uma vez; em empate, o chunk_id menor vence.
    assert [result.chunk.chunk_id for result in results] == ["a", "c"]
    assert len({result.chunk.text for result in results}) == len(results)
    assert all(result.score >= 0.5 for result in results)


def test_unknown_or_blank_query_returns_no_result() -> None:
    retriever = HybridRetriever(
        [make_chunk("pix", "pagamento por pix")],
        auto_embeddings=False,
        min_score=0.0,
    )

    assert retriever.search("   ") == []
    assert retriever.search("vocabulário-inexistente") == []


def test_character_search_keeps_useful_typo_tolerance() -> None:
    retriever = HybridRetriever(
        [
            make_chunk("pix", "pagamento por pix"),
            make_chunk("garantia", "defeito de fabricação coberto pela garantia"),
        ],
        auto_embeddings=False,
        min_score=0.0,
    )

    results = retriever.search("pagament por piks")

    assert results
    assert results[0].chunk.chunk_id == "pix"


def test_invalid_parameters_are_rejected() -> None:
    chunk = make_chunk("pix", "pagamento por pix")

    with pytest.raises(ValueError, match="top_k"):
        HybridRetriever([chunk], top_k=0)
    with pytest.raises(ValueError, match="min_score"):
        HybridRetriever([chunk], min_score=1.1)
    with pytest.raises(ValueError, match="peso"):
        HybridRetriever([chunk], semantic_weight=0, lexical_weight=0)
