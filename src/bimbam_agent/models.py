"""Objetos de domínio compartilhados pelo pipeline RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentFragment:
    """Trecho extraído de uma localização lógica do documento."""

    text: str
    source_name: str
    source_path: Path
    location: str
    page: int | None = None
    section: str | None = None
    category: str = "Geral"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Chunk:
    """Unidade indexável com metadados rastreáveis."""

    chunk_id: str
    text: str
    source_name: str
    source_path: Path
    location: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    category: str = "Geral"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        parts = [self.source_name]
        if self.section:
            parts.append(self.section)
        if self.page_start is not None:
            page_label = f"p. {self.page_start}"
            if self.page_end and self.page_end != self.page_start:
                page_label = f"p. {self.page_start}-{self.page_end}"
            parts.append(page_label)
        return " - ".join(parts)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Resultado recuperado pelo índice híbrido."""

    chunk: Chunk
    score: float
    semantic_score: float = 0.0
    lexical_score: float = 0.0


@dataclass(frozen=True, slots=True)
class AgentAnswer:
    """Resposta final e evidências usadas para produzi-la."""

    text: str
    sources: tuple[SearchResult, ...]
    grounded: bool
    mode: str
