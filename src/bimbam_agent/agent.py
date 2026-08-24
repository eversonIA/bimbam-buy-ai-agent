"""Orquestração do fluxo de recuperação e geração (RAG)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .config import Settings
from .generation import (
    NO_INFORMATION_MESSAGE,
    ExtractiveGenerator,
    GeminiGenerator,
    ResponseGenerator,
)
from .models import AgentAnswer

LIVE_DATA_UNAVAILABLE_MESSAGE = (
    "Não tenho acesso aos sistemas transacionais da BimBam Buy e, por isso, não consigo "
    "consultar o status atual de um pedido específico. Posso explicar os prazos e "
    "procedimentos gerais descritos na base documental."
)


def _normalize_query(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9#]+", value))


def _requires_live_order_access(question: str) -> bool:
    normalized = _normalize_query(question)
    return bool(
        "status atual" in normalized
        or "onde esta meu pedido" in normalized
        or "localizacao atual" in normalized
        or re.search(r"\bpedido\s*#?\s*\d{4,}\b", normalized)
    )


def _requested_contact_kind(question: str) -> str | None:
    normalized = _normalize_query(question)
    if "telefone" in normalized or "whatsapp" in normalized:
        return "phone"
    if "e mail" in normalized or "email" in normalized:
        return "email"
    if any(term in normalized.split() for term in ("url", "site", "link")):
        return "url"
    if "endereco" in normalized:
        return "address"
    if "contato" in normalized:
        return "contact"
    return None


def _contains_concrete_contact(text: str, kind: str) -> bool:
    checks = {
        "phone": bool(re.search(r"(?<!\d)\+?\d[\d\s().-]{6,}\d(?!\d)", text)),
        "email": bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)),
        "url": bool(re.search(r"https?://|www\.", text, re.IGNORECASE)),
        "address": bool(
            re.search(r"\b(?:rua|avenida|av\.|rodovia|alameda|travessa)\b", text, re.IGNORECASE)
        ),
    }
    if kind == "contact":
        return any(checks.values())
    return checks[kind]


class KnowledgeAgent:
    """Consulta o índice e responde somente com as evidências recuperadas."""

    def __init__(
        self,
        retriever: Any,
        generator: ResponseGenerator,
        *,
        fallback_generator: ResponseGenerator | None = None,
        top_k: int = 5,
        min_score: float = 0.12,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.fallback_generator = fallback_generator or ExtractiveGenerator()
        self.top_k = top_k
        self.min_score = min_score

    @property
    def mode(self) -> str:
        return self.generator.mode

    def ask(
        self,
        question: str,
        history: Sequence[Mapping[str, str]] | None = None,
    ) -> AgentAnswer:
        """Responda a uma pergunta e devolva também as fontes auditáveis."""

        clean_question = question.strip()
        if not clean_question:
            return AgentAnswer(
                text="Digite uma pergunta para consultar a base de conhecimento.",
                sources=(),
                grounded=False,
                mode="sem_consulta",
            )

        if _requires_live_order_access(clean_question):
            return AgentAnswer(
                text=LIVE_DATA_UNAVAILABLE_MESSAGE,
                sources=(),
                grounded=False,
                mode="dados_ao_vivo_indisponiveis",
            )

        results = self.retriever.search(
            clean_question,
            top_k=self.top_k,
            min_score=self.min_score,
        )
        sources = tuple(results)
        if not sources:
            return AgentAnswer(
                text=NO_INFORMATION_MESSAGE,
                sources=(),
                grounded=False,
                mode="sem_resultados",
            )

        contact_kind = _requested_contact_kind(clean_question)
        if contact_kind and not any(
            _contains_concrete_contact(result.chunk.text, contact_kind) for result in sources
        ):
            return AgentAnswer(
                text=NO_INFORMATION_MESSAGE,
                sources=(),
                grounded=False,
                mode="sem_resultados",
            )

        try:
            text = self.generator.generate(clean_question, sources, history)
            mode = self.generator.mode
        except Exception:
            # Falha de rede, cota, credencial ou validação nunca impede uma resposta local.
            text = self.fallback_generator.generate(clean_question, sources, history)
            mode = f"{self.fallback_generator.mode} (fallback)"

        grounded = text != NO_INFORMATION_MESSAGE
        return AgentAnswer(text=text, sources=sources, grounded=grounded, mode=mode)


def build_knowledge_agent(settings: Settings | None = None) -> KnowledgeAgent:
    """Carregue a base local e construa o agente pronto para uso.

    Os imports ficam dentro da função para manter os componentes desacoplados e permitir
    testes unitários com fakes sem inicializar leitores de arquivos ou índices.
    """

    from .chunking import chunk_fragments
    from .ingestion import load_documents
    from .retrieval import HybridRetriever

    settings = settings or Settings.from_env()
    fragments = load_documents(settings.documents_dir, settings.manifest_path)
    chunks = chunk_fragments(fragments)
    # Passar explicitamente o objeto é importante no Streamlit: a chave pode vir
    # de st.secrets sem existir como variável de ambiente do processo.
    retriever = HybridRetriever(chunks, settings=settings)

    fallback = ExtractiveGenerator()
    generator: ResponseGenerator
    if settings.gemini_api_key:
        generator = GeminiGenerator(
            api_key=settings.gemini_api_key,
            model=settings.generation_model,
        )
    else:
        generator = fallback

    return KnowledgeAgent(
        retriever,
        generator,
        fallback_generator=fallback,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )


# Nome curto conveniente para scripts e integrações.
build_agent = build_knowledge_agent
