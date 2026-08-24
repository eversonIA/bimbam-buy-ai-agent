"""Testes de integração contra os cinco PDFs reais do challenge."""

from __future__ import annotations

import pytest

from bimbam_agent.agent import (
    LIVE_DATA_UNAVAILABLE_MESSAGE,
    KnowledgeAgent,
    build_knowledge_agent,
)
from bimbam_agent.chunking import chunk_fragments
from bimbam_agent.config import Settings
from bimbam_agent.generation import NO_INFORMATION_MESSAGE, ExtractiveGenerator
from bimbam_agent.ingestion import load_documents
from bimbam_agent.retrieval import HybridRetriever


@pytest.fixture(scope="module")
def knowledge_base():
    settings = Settings(gemini_api_key=None)
    fragments = load_documents(settings.documents_dir, settings.manifest_path)
    chunks = chunk_fragments(fragments)
    retriever = HybridRetriever(
        chunks,
        auto_embeddings=False,
        top_k=5,
        min_score=0.0,
    )
    return fragments, chunks, retriever


def test_real_knowledge_base_is_complete_and_traceable(knowledge_base) -> None:
    fragments, chunks, _ = knowledge_base

    assert len({fragment.source_name for fragment in fragments}) == 5
    assert len(fragments) == 55
    assert len(chunks) == 93
    assert all(chunk.source_name and chunk.location for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


@pytest.mark.parametrize(
    ("question", "expected_category"),
    [
        ("Quanto tempo o boleto leva para ser confirmado?", "Pagamentos"),
        ("Qual é o prazo para comunicar dano no transporte?", "Logística"),
        ("Dano causado por líquido é coberto pela garantia?", "Garantia"),
        ("Qual é o prazo para desistir da compra recebida?", "Pós-venda"),
        ("Venda cancelada gera comissão para o afiliado?", "Afiliados"),
    ],
)
def test_known_questions_retrieve_the_right_business_area(
    knowledge_base,
    question: str,
    expected_category: str,
) -> None:
    _, _, retriever = knowledge_base

    results = retriever.search(question, top_k=5, min_score=0.0)

    assert results
    assert expected_category in {result.chunk.category for result in results}


def test_real_agent_refuses_missing_contact_and_live_order_status(knowledge_base) -> None:
    _, _, retriever = knowledge_base
    agent = KnowledgeAgent(
        retriever,
        ExtractiveGenerator(),
        top_k=5,
        min_score=0.0,
    )

    contact = agent.ask("Qual é o telefone oficial da central de ajuda?")
    live_status = agent.ask("Qual é o status atual do pedido 12345?")

    assert contact.text == NO_INFORMATION_MESSAGE
    assert contact.grounded is False
    assert live_status.text == LIVE_DATA_UNAVAILABLE_MESSAGE
    assert live_status.grounded is False


def test_application_factory_builds_an_offline_agent() -> None:
    agent = build_knowledge_agent(Settings(gemini_api_key=None))

    answer = agent.ask("Quanto tempo o boleto leva para ser confirmado?")

    assert agent.mode == "extrativo"
    assert answer.grounded is True
    assert "[Fonte" in answer.text
    assert any(result.chunk.category == "Pagamentos" for result in answer.sources)


def test_offline_agent_lists_all_accepted_payment_methods(knowledge_base) -> None:
    _, _, retriever = knowledge_base
    agent = KnowledgeAgent(
        retriever,
        ExtractiveGenerator(),
        top_k=5,
        min_score=0.0,
    )

    answer = agent.ask("Quais formas de pagamento são aceitas?")

    assert answer.grounded is True
    assert answer.sources[0].chunk.category == "Pagamentos"
    assert "Cartão de crédito" in answer.text
    assert "Cartão de débito" in answer.text
    assert "Transferência bancária / PIX" in answer.text
    assert "Pagamento em dinheiro em pontos habilitados" in answer.text
    assert "Carteiras digitais" in answer.text
    assert "Parcelamento ou financiamento" in answer.text


def test_offline_agent_prioritizes_warranty_coverage_over_exclusions(
    knowledge_base,
) -> None:
    _, _, retriever = knowledge_base
    agent = KnowledgeAgent(
        retriever,
        ExtractiveGenerator(),
        top_k=5,
        min_score=0.0,
    )

    answer = agent.ask("O que a garantia cobre?")

    assert answer.grounded is True
    assert answer.sources[0].chunk.category == "Garantia"
    assert "Falha ao ligar" in answer.text
    assert "Mau funcionamento de componentes" in answer.text
    assert "Defeitos de montagem" in answer.text
    assert "Problemas de fabricação" in answer.text
    assert "A garantia não cobre" not in answer.text


def test_offline_agent_explains_how_to_track_a_shipment(knowledge_base) -> None:
    _, _, retriever = knowledge_base
    agent = KnowledgeAgent(
        retriever,
        ExtractiveGenerator(),
        top_k=5,
        min_score=0.0,
    )

    answer = agent.ask("Como acompanho o envio do meu pedido?")

    assert answer.grounded is True
    assert answer.sources[0].chunk.category == "Logística"
    assert "O cliente pode verificar o status do pedido" in answer.text
    assert "Número do pedido" in answer.text
    assert "E-mail cadastrado" in answer.text
    assert "Link de rastreamento" in answer.text
