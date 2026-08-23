"""Divisão estrutural e determinística dos fragmentos para indexação."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

from .ingestion import clean_text
from .models import Chunk, DocumentFragment

DEFAULT_CHUNK_SIZE = 1_200
DEFAULT_CHUNK_OVERLAP = 160


def chunk_fragments(
    fragments: Iterable[DocumentFragment],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Converte fragmentos em chunks sem cruzar suas fronteiras lógicas.

    ``chunk_size`` e ``overlap`` são medidos em caracteres. Os cortes dão
    preferência, nesta ordem, a parágrafos, linhas, frases e palavras.
    """

    _validate_limits(chunk_size, overlap)
    chunks: list[Chunk] = []
    for fragment in fragments:
        chunks.extend(chunk_fragment(fragment, chunk_size=chunk_size, overlap=overlap))
    return chunks


def chunk_fragment(
    fragment: DocumentFragment,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Divide um único fragmento, preservando sua fonte e seus metadados."""

    _validate_limits(chunk_size, overlap)
    text = clean_text(fragment.text)
    if not text:
        return []

    pieces = split_text(text, chunk_size=chunk_size, overlap=overlap)
    chunks: list[Chunk] = []
    for index, piece in enumerate(pieces):
        metadata = dict(fragment.metadata)
        metadata.update({"chunk_index": index, "chunk_count": len(pieces)})
        chunks.append(
            Chunk(
                chunk_id=_chunk_id(fragment, index, piece),
                text=piece,
                source_name=fragment.source_name,
                source_path=fragment.source_path,
                location=fragment.location,
                page_start=fragment.page,
                page_end=fragment.page,
                section=fragment.section,
                category=fragment.category,
                metadata=metadata,
            )
        )
    return chunks


def split_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Divide texto com limite rígido de tamanho e sobreposição máxima."""

    _validate_limits(chunk_size, overlap)
    normalized = clean_text(text)
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    pieces: list[str] = []
    start = 0
    text_length = len(normalized)
    while start < text_length:
        hard_end = min(start + chunk_size, text_length)
        end = hard_end if hard_end == text_length else _best_boundary(normalized, start, hard_end)
        if end <= start:
            end = hard_end

        piece = normalized[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= text_length:
            break

        next_start = max(start + 1, end - overlap)
        # Avançar até uma fronteira evita começar no meio de uma palavra e
        # garante que a sobreposição real nunca seja maior que a solicitada.
        if next_start > 0 and next_start < text_length:
            while (
                next_start < end
                and normalized[next_start - 1].isalnum()
                and normalized[next_start].isalnum()
            ):
                next_start += 1
            while next_start < text_length and normalized[next_start].isspace():
                next_start += 1
        if next_start <= start:
            next_start = end
        start = next_start

    return pieces


def _best_boundary(text: str, start: int, hard_end: int) -> int:
    # Evita produzir um primeiro pedaço excessivamente curto apenas porque há
    # uma quebra logo depois do início da janela.
    minimum = start + max(1, int((hard_end - start) * 0.55))
    window = text[minimum:hard_end]

    for separator in ("\n\n", "\n"):
        position = window.rfind(separator)
        if position >= 0:
            return minimum + position + len(separator)

    sentence_ends = list(re.finditer(r"[.!?](?:[\"'”’\)\]]*)\s+", window))
    if sentence_ends:
        return minimum + sentence_ends[-1].end()

    position = window.rfind(" ")
    if position >= 0:
        return minimum + position + 1
    return hard_end


def _validate_limits(chunk_size: int, overlap: int) -> None:
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size <= 0:
        raise ValueError("chunk_size deve ser um inteiro maior que zero")
    if not isinstance(overlap, int) or isinstance(overlap, bool) or overlap < 0:
        raise ValueError("overlap deve ser um inteiro maior ou igual a zero")
    if overlap >= chunk_size:
        raise ValueError("overlap deve ser menor que chunk_size")


def _chunk_id(fragment: DocumentFragment, index: int, text: str) -> str:
    identity = {
        "source": fragment.source_name,
        "file": fragment.source_path.name,
        "location": fragment.location,
        "page": fragment.page,
        "section": fragment.section,
        "index": index,
        "text": text,
    }
    serialized = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:20]
    return f"chunk_{digest}"


# Nome alternativo útil para consumidores que tratam a saída como um corpus.
build_chunks = chunk_fragments


__all__ = [
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "build_chunks",
    "chunk_fragment",
    "chunk_fragments",
    "split_text",
]
