from __future__ import annotations

from pathlib import Path

import pytest

from bimbam_agent.chunking import chunk_fragment, chunk_fragments, split_text
from bimbam_agent.models import DocumentFragment


def _fragment(
    text: str,
    *,
    name: str = "manual.pdf",
    page: int | None = 4,
    section: str | None = "Garantia",
) -> DocumentFragment:
    return DocumentFragment(
        text=text,
        source_name=name,
        source_path=Path("data") / name,
        location="Página 4" if page else "Documento",
        page=page,
        section=section,
        category="Pós-venda",
        metadata={"language": "pt-BR", "version": "1"},
    )


def test_short_fragment_becomes_one_traceable_chunk() -> None:
    fragment = _fragment("A garantia cobre defeitos de fabricação.")

    chunks = chunk_fragment(fragment)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.text == fragment.text
    assert chunk.source_name == fragment.source_name
    assert chunk.source_path == fragment.source_path
    assert chunk.location == fragment.location
    assert chunk.page_start == chunk.page_end == 4
    assert chunk.section == "Garantia"
    assert chunk.category == "Pós-venda"
    assert chunk.citation == "manual.pdf - Garantia - p. 4"
    assert chunk.metadata == {
        "language": "pt-BR",
        "version": "1",
        "chunk_index": 0,
        "chunk_count": 1,
    }
    assert fragment.metadata == {"language": "pt-BR", "version": "1"}


def test_long_text_respects_size_and_overlap() -> None:
    text = " ".join(f"palavra{i:03d}" for i in range(180))

    pieces = split_text(text, chunk_size=180, overlap=35)

    assert len(pieces) > 2
    assert all(0 < len(piece) <= 180 for piece in pieces)
    starts = [text.index(piece) for piece in pieces]
    for previous_start, previous, current_start in zip(starts, pieces, starts[1:], strict=False):
        actual_overlap = previous_start + len(previous) - current_start
        assert 0 <= actual_overlap <= 35


def test_split_prefers_structural_boundaries() -> None:
    first = "Primeiro parágrafo com uma ideia completa."
    second = "Segundo parágrafo com outra ideia e mais detalhes para o leitor."
    text = f"{first}\n\n{second}"

    pieces = split_text(text, chunk_size=70, overlap=0)

    assert pieces[0] == first
    assert pieces[1] == second


def test_chunk_ids_are_deterministic_and_content_sensitive() -> None:
    fragment = _fragment("Texto base. " * 80)

    first_run = chunk_fragment(fragment, chunk_size=160, overlap=20)
    second_run = chunk_fragment(fragment, chunk_size=160, overlap=20)
    changed = chunk_fragment(_fragment("Texto alterado. " * 80), chunk_size=160, overlap=20)

    assert [chunk.chunk_id for chunk in first_run] == [chunk.chunk_id for chunk in second_run]
    assert len({chunk.chunk_id for chunk in first_run}) == len(first_run)
    assert first_run[0].chunk_id != changed[0].chunk_id
    assert all(chunk.chunk_id.startswith("chunk_") for chunk in first_run)


def test_fragments_never_mix_and_keep_their_own_citations() -> None:
    first = _fragment("Conteúdo de pagamentos", name="pagamentos.pdf", page=1, section="Pix")
    second = _fragment("Conteúdo de envios", name="envios.pdf", page=8, section="Prazo")

    chunks = chunk_fragments([first, second], chunk_size=100, overlap=10)

    assert len(chunks) == 2
    assert chunks[0].source_name == "pagamentos.pdf"
    assert chunks[0].citation == "pagamentos.pdf - Pix - p. 1"
    assert chunks[1].source_name == "envios.pdf"
    assert chunks[1].citation == "envios.pdf - Prazo - p. 8"


def test_empty_fragment_is_ignored() -> None:
    assert chunk_fragment(_fragment(" \n\n ")) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (100, -1), (100, 100), (100, 101), (True, 0)],
)
def test_invalid_chunk_limits_are_rejected(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        split_text("conteúdo", chunk_size=chunk_size, overlap=overlap)
