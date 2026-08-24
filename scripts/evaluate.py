"""Executa uma avaliação offline e reproduzível da recuperação documental."""

from __future__ import annotations

import json
import re
import unicodedata

from bimbam_agent.agent import KnowledgeAgent
from bimbam_agent.chunking import chunk_fragments
from bimbam_agent.config import PROJECT_ROOT, Settings
from bimbam_agent.generation import ExtractiveGenerator
from bimbam_agent.ingestion import load_documents
from bimbam_agent.retrieval import HybridRetriever


def _normalize(text: str) -> str:
    """Normalize acentos, caixa e espaços para uma validação textual estável."""

    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def main() -> int:
    settings = Settings(gemini_api_key=None)
    fragments = load_documents(settings.documents_dir, settings.manifest_path)
    chunks = chunk_fragments(fragments)
    retriever = HybridRetriever(
        chunks,
        auto_embeddings=False,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )
    agent = KnowledgeAgent(
        retriever,
        ExtractiveGenerator(),
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )

    cases_path = PROJECT_ROOT / "evals" / "questions.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    passed = 0

    print(f"Base: {len(fragments)} fragmentos, {len(chunks)} chunks")
    for case in cases:
        answer = agent.ask(case["question"])
        expected_source = case.get("expected_source")
        if expected_source:
            source_ok = any(
                expected_source.casefold() in result.chunk.source_name.casefold()
                for result in answer.sources
            )
        else:
            source_ok = not answer.grounded

        normalized_answer = _normalize(answer.text)
        missing_terms = [
            term
            for term in case.get("expected_terms", [])
            if _normalize(term) not in normalized_answer
        ]
        terms_ok = not missing_terms
        case_ok = source_ok and terms_ok
        status = "PASS" if case_ok else "FAIL"
        passed += int(case_ok)
        print(f"[{status}] {case['id']}: {case['question']}")
        if answer.sources:
            print(f"       fonte principal: {answer.sources[0].chunk.citation}")
        else:
            print(f"       resposta: {answer.text}")
        if not source_ok:
            print("       fonte esperada não recuperada")
        if missing_terms:
            print(f"       termos ausentes: {', '.join(missing_terms)}")

    total = len(cases)
    print(f"\nResultado: {passed}/{total} casos aprovados")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
