"""Recuperação híbrida, local e tolerante a falhas para o pipeline RAG.

O índice lexical é sempre construído localmente com TF-IDF. Embeddings são um
reforço opcional: qualquer indisponibilidade do provedor semântico faz a busca
continuar apenas com o índice lexical.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Any, Protocol, runtime_checkable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from bimbam_agent.config import Settings
from bimbam_agent.models import Chunk, SearchResult

# Similaridade de caracteres ajuda com pequenos erros de digitação, mas qualquer
# n-grama acidental não deve transformar uma consulta desconhecida em um resultado 1.0
# depois da normalização relativa.
_MIN_LEXICAL_SIGNAL = 0.015


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Contrato mínimo para provedores de embeddings intercambiáveis."""

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Gera um vetor para cada documento, preservando a ordem de entrada."""

    def embed_query(self, text: str) -> Sequence[float]:
        """Gera o vetor de uma consulta."""


class GeminiEmbeddingProvider:
    """Adaptador pequeno para a API de embeddings do ``google-genai``.

    O import do SDK é adiado até a criação do cliente. Assim, a recuperação
    lexical continua utilizável mesmo se o SDK não estiver instalado no ambiente.
    Um cliente pode ser injetado para testes, sem realizar chamadas de rede.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "gemini-embedding-001",
        output_dimensionality: int | None = 768,
        batch_size: int = 100,
        client: Any | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model não pode ser vazio")
        if output_dimensionality is not None and output_dimensionality <= 0:
            raise ValueError("output_dimensionality deve ser positivo")
        if batch_size <= 0:
            raise ValueError("batch_size deve ser positivo")

        resolved_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        if client is None:
            if not resolved_key:
                raise ValueError("GEMINI_API_KEY não configurada")
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - depende do ambiente
                raise RuntimeError("google-genai não está instalado") from exc
            client = genai.Client(api_key=resolved_key)

        self._client = client
        self.model = model
        self.output_dimensionality = output_dimensionality
        self.batch_size = batch_size

    @classmethod
    def from_settings(cls, settings: Settings) -> GeminiEmbeddingProvider:
        """Cria o provedor com a mesma configuração usada pela aplicação."""

        return cls(
            api_key=settings.gemini_api_key,
            model=settings.embedding_model,
            output_dimensionality=settings.embedding_dimension,
        )

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        clean_texts = [str(text) for text in texts]
        if not clean_texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(clean_texts), self.batch_size):
            batch = clean_texts[start : start + self.batch_size]
            vectors.extend(self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed_batch([str(text)], task_type="RETRIEVAL_QUERY")
        if len(vectors) != 1:
            raise RuntimeError("A API Gemini retornou uma quantidade inválida de embeddings")
        return vectors[0]

    def _embed_batch(self, texts: Sequence[str], *, task_type: str) -> list[list[float]]:
        try:
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise RuntimeError("google-genai não está instalado") from exc

        config_kwargs: dict[str, Any] = {"task_type": task_type}
        if self.output_dimensionality is not None:
            config_kwargs["output_dimensionality"] = self.output_dimensionality

        response = self._client.models.embed_content(
            model=self.model,
            contents=list(texts),
            config=types.EmbedContentConfig(**config_kwargs),
        )
        embeddings = getattr(response, "embeddings", None)
        if embeddings is None or len(embeddings) != len(texts):
            raise RuntimeError("A API Gemini retornou embeddings incompletos")

        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = getattr(embedding, "values", None)
            if values is None:
                raise RuntimeError("A API Gemini retornou um embedding sem valores")
            vectors.append([float(value) for value in values])
        return vectors


class HybridRetriever:
    """Índice híbrido em memória apropriado para uma base documental pequena.

    Os escores lexical e semântico são normalizados para ``[0, 1]`` antes da
    combinação. Se apenas um canal produzir sinal, seu escore é usado integralmente.
    Isso também garante o fallback lexical quando embeddings falham.
    """

    def __init__(
        self,
        chunks: Iterable[Chunk],
        embedding_provider: EmbeddingProvider | None = None,
        *,
        settings: Settings | None = None,
        semantic_weight: float = 0.55,
        lexical_weight: float = 0.45,
        top_k: int | None = None,
        min_score: float | None = None,
        auto_embeddings: bool = True,
    ) -> None:
        self.chunks = tuple(chunks)
        resolved_settings = settings or Settings.from_env()

        self.semantic_weight = self._validate_weight(semantic_weight, "semantic_weight")
        self.lexical_weight = self._validate_weight(lexical_weight, "lexical_weight")
        if self.semantic_weight == 0 and self.lexical_weight == 0:
            raise ValueError("ao menos um peso de recuperação deve ser positivo")

        self.top_k = self._validate_top_k(
            resolved_settings.retrieval_top_k if top_k is None else top_k
        )
        self.min_score = self._validate_min_score(
            resolved_settings.retrieval_min_score if min_score is None else min_score
        )

        self._vectorizer: FeatureUnion | None = None
        self._lexical_matrix: Any | None = None
        self._build_lexical_index()

        self.embedding_provider = embedding_provider
        self.semantic_error: str | None = None
        self._document_embeddings: np.ndarray | None = None

        if (
            self.embedding_provider is None
            and auto_embeddings
            and self.semantic_weight > 0
            and resolved_settings.gemini_api_key
        ):
            try:
                self.embedding_provider = GeminiEmbeddingProvider.from_settings(resolved_settings)
            except Exception as exc:  # o índice lexical deve continuar funcional
                self.semantic_error = self._format_error(exc)

        if self.embedding_provider is not None and self.semantic_weight > 0 and self.chunks:
            self._build_semantic_index()

    @property
    def semantic_available(self) -> bool:
        """Indica se os embeddings dos documentos estão prontos para consulta."""

        return self._document_embeddings is not None

    @property
    def lexical_available(self) -> bool:
        """Indica se o corpus contém vocabulário lexical indexável."""

        return self._vectorizer is not None and self._lexical_matrix is not None

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Retorna os chunks mais relevantes, com ordenação determinística."""

        if not isinstance(query, str):
            raise TypeError("query deve ser uma string")
        clean_query = " ".join(query.split())
        if not clean_query or not self.chunks:
            return []

        result_limit = self.top_k if top_k is None else self._validate_top_k(top_k)
        threshold = self.min_score if min_score is None else self._validate_min_score(min_score)

        lexical_scores, has_lexical_signal = self._lexical_scores(clean_query)
        semantic_scores, has_semantic_signal = self._semantic_scores(clean_query)

        if not has_lexical_signal and not has_semantic_signal:
            return []

        if has_lexical_signal and has_semantic_signal:
            weight_sum = self.lexical_weight + self.semantic_weight
            combined_scores = (
                self.lexical_weight * lexical_scores + self.semantic_weight * semantic_scores
            ) / weight_sum
        elif has_semantic_signal:
            combined_scores = semantic_scores
        else:
            # Fallback deliberadamente ignora o peso: TF-IDF deve permanecer útil
            # mesmo quando o canal semântico configurado estiver indisponível.
            combined_scores = lexical_scores

        candidates: list[tuple[int, SearchResult]] = []
        for index, chunk in enumerate(self.chunks):
            score = float(np.clip(combined_scores[index], 0.0, 1.0))
            if score + 1e-12 < threshold:
                continue
            candidates.append(
                (
                    index,
                    SearchResult(
                        chunk=chunk,
                        score=score,
                        semantic_score=float(np.clip(semantic_scores[index], 0.0, 1.0)),
                        lexical_score=float(np.clip(lexical_scores[index], 0.0, 1.0)),
                    ),
                )
            )

        candidates.sort(key=self._sort_key)

        results: list[SearchResult] = []
        seen_ids: set[str] = set()
        seen_texts: set[str] = set()
        for _, result in candidates:
            normalized_id = result.chunk.chunk_id.strip().casefold()
            normalized_text = " ".join(result.chunk.text.split()).casefold()
            if normalized_id and normalized_id in seen_ids:
                continue
            if normalized_text and normalized_text in seen_texts:
                continue
            if normalized_id:
                seen_ids.add(normalized_id)
            if normalized_text:
                seen_texts.add(normalized_text)
            results.append(result)
            if len(results) >= result_limit:
                break
        return results

    def _build_lexical_index(self) -> None:
        if not self.chunks:
            return
        vectorizer = FeatureUnion(
            [
                (
                    "words",
                    TfidfVectorizer(
                        lowercase=True,
                        strip_accents="unicode",
                        ngram_range=(1, 2),
                        token_pattern=r"(?u)\b\w+\b",
                        sublinear_tf=True,
                        norm="l2",
                    ),
                ),
                (
                    "characters",
                    TfidfVectorizer(
                        analyzer="char_wb",
                        lowercase=True,
                        strip_accents="unicode",
                        ngram_range=(3, 5),
                        sublinear_tf=True,
                        norm="l2",
                    ),
                ),
            ],
            transformer_weights={"words": 0.7, "characters": 0.3},
        )
        try:
            matrix = vectorizer.fit_transform(
                [self._lexical_document(chunk) for chunk in self.chunks]
            )
        except ValueError as exc:
            # Um corpus composto apenas de espaços/pontuação não tem vocabulário.
            if "empty vocabulary" not in str(exc).lower():
                raise
            return
        self._vectorizer = vectorizer
        self._lexical_matrix = matrix

    def _build_semantic_index(self) -> None:
        assert self.embedding_provider is not None
        try:
            raw_vectors = self.embedding_provider.embed_documents(
                [chunk.text for chunk in self.chunks]
            )
            matrix = self._coerce_matrix(raw_vectors, expected_rows=len(self.chunks))
            self._document_embeddings = self._normalize_rows(matrix)
            self.semantic_error = None
        except Exception as exc:
            self._document_embeddings = None
            self.semantic_error = self._format_error(exc)

    def _lexical_scores(self, query: str) -> tuple[np.ndarray, bool]:
        empty_scores = np.zeros(len(self.chunks), dtype=float)
        if not self.lexical_available:
            return empty_scores, False

        assert self._vectorizer is not None
        query_vector = self._vectorizer.transform([self._expand_lexical_query(query)])
        if query_vector.nnz == 0:
            return empty_scores, False

        raw_scores = (self._lexical_matrix @ query_vector.T).toarray().reshape(-1)
        if float(raw_scores.max(initial=0.0)) < _MIN_LEXICAL_SIGNAL:
            return empty_scores, False
        scores = self._normalize_scores(raw_scores)
        return scores, bool(np.any(scores > 0))

    def _semantic_scores(self, query: str) -> tuple[np.ndarray, bool]:
        empty_scores = np.zeros(len(self.chunks), dtype=float)
        if self._document_embeddings is None or self.embedding_provider is None:
            return empty_scores, False

        try:
            raw_query = self.embedding_provider.embed_query(query)
            query_matrix = self._coerce_matrix([raw_query], expected_rows=1)
            if query_matrix.shape[1] != self._document_embeddings.shape[1]:
                raise ValueError("dimensão do embedding da consulta é incompatível")
            query_vector = self._normalize_rows(query_matrix)[0]
            if not np.any(query_vector):
                return empty_scores, False
            cosine_scores = self._document_embeddings @ query_vector
            scores = self._normalize_scores(cosine_scores)
            self.semantic_error = None
            return scores, bool(np.any(scores > 0))
        except Exception as exc:
            self.semantic_error = self._format_error(exc)
            return empty_scores, False

    @staticmethod
    def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms > 0)

    @staticmethod
    def _normalize_scores(raw_scores: Sequence[float] | np.ndarray) -> np.ndarray:
        scores = np.asarray(raw_scores, dtype=float).reshape(-1)
        scores = np.where(np.isfinite(scores), scores, 0.0)
        # Similaridades negativas não representam evidência recuperável.
        scores = np.clip(scores, 0.0, None)
        maximum = float(scores.max(initial=0.0))
        if maximum <= 0:
            return np.zeros_like(scores)
        return np.clip(scores / maximum, 0.0, 1.0)

    @staticmethod
    def _coerce_matrix(
        values: Sequence[Sequence[float]] | np.ndarray,
        *,
        expected_rows: int,
    ) -> np.ndarray:
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim == 1 and expected_rows == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.ndim != 2 or matrix.shape[0] != expected_rows or matrix.shape[1] == 0:
            raise ValueError("provedor retornou embeddings com formato inválido")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("provedor retornou embeddings não finitos")
        return matrix

    @staticmethod
    def _sort_key(item: tuple[int, SearchResult]) -> tuple[Any, ...]:
        index, result = item
        chunk = result.chunk
        return (
            -result.score,
            -result.semantic_score,
            -result.lexical_score,
            chunk.chunk_id.casefold(),
            chunk.source_name.casefold(),
            chunk.location.casefold(),
            index,
        )

    @staticmethod
    def _validate_weight(value: float, name: str) -> float:
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"{name} deve ser um número finito não negativo")
        return number

    @staticmethod
    def _validate_top_k(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("top_k deve ser um inteiro positivo")
        return value

    @staticmethod
    def _validate_min_score(value: float) -> float:
        number = float(value)
        if not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError("min_score deve estar entre 0 e 1")
        return number

    @staticmethod
    def _format_error(exc: Exception) -> str:
        message = str(exc).strip()
        return f"{type(exc).__name__}: {message}" if message else type(exc).__name__

    @staticmethod
    def _lexical_document(chunk: Chunk) -> str:
        title = str(chunk.metadata.get("title", ""))
        section = chunk.section or ""
        return "\n".join(value for value in (chunk.category, title, section, chunk.text) if value)

    @staticmethod
    def _expand_lexical_query(query: str) -> str:
        """Acrescenta equivalências pequenas para variações comuns em português."""

        normalized = unicodedata.normalize("NFKD", query.casefold())
        normalized = "".join(
            character for character in normalized if not unicodedata.combining(character)
        )
        expansions: list[str] = []
        rules = (
            (r"\bcancelad\w*\b", "cancelamento cancelamentos anulação"),
            (r"\bdanificad\w*\b", "dano danos avaria"),
            (r"\btransporte\b", "trânsito logística"),
            (r"\bdesist\w*\b", "arrependimento devolução devolver"),
            (r"\brastre\w*\b", "rastreamento tracking acompanhamento"),
            (r"\bliquid\w*\b", "líquido líquidos umidade"),
        )
        for pattern, synonyms in rules:
            if re.search(pattern, normalized):
                expansions.append(synonyms)

        # "Formas de pagamento" e "métodos aceitos" descrevem o mesmo conceito.
        # A expansão inclui os nomes presentes na lista oficial para superar ruído de
        # índice, cabeçalhos e ocorrências genéricas de "meio de pagamento".
        asks_for_payment_methods = bool(
            re.search(r"\bpagamentos?\b", normalized)
            and re.search(
                r"\b(?:forma|formas|metodo|metodos|meio|meios|opcao|opcoes)\b",
                normalized,
            )
            and re.search(r"\b(?:aceit\w*|disponiv\w*|oferec\w*|quais)\b", normalized)
        )
        if asks_for_payment_methods:
            expansions.append(
                "métodos de pagamento disponíveis aceitar cartão de crédito "
                "cartão de débito transferência bancária PIX pagamento em dinheiro "
                "Boleto carteiras digitais parcelamento financiamento"
            )

        asks_for_warranty_coverage = bool(
            re.search(r"\bgarantia\b", normalized)
            and re.search(r"\bcobr\w*\b", normalized)
            and not re.search(r"\b(?:nao|exclu\w*|fora)\b", normalized)
        )
        if asks_for_warranty_coverage:
            expansions.append(
                "cobertura geral garantia pode cobrir coberto defeito defeitos "
                "falha falhas fabricação montagem funcionamento"
            )

        asks_for_shipment_tracking = bool(
            re.search(r"\b(?:rastre\w*|acompanh\w*)\b", normalized)
            and re.search(r"\b(?:envio|envios|entrega|entregas|pedido|pedidos)\b", normalized)
        )
        if asks_for_shipment_tracking:
            expansions.append(
                "rastreamento acompanhamento verificar status do pedido número do pedido "
                "e-mail cadastrado link de rastreamento"
            )
        return " ".join((query, *expansions))


__all__ = ["EmbeddingProvider", "GeminiEmbeddingProvider", "HybridRetriever"]
