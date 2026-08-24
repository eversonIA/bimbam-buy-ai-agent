"""Configuração central do aplicativo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifest.json"


@dataclass(frozen=True, slots=True)
class Settings:
    gemini_api_key: str | None
    generation_model: str = "gemini-3.7-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.12
    documents_dir: Path = DEFAULT_DOCUMENTS_DIR
    manifest_path: Path = DEFAULT_MANIFEST_PATH

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        api_key = os.getenv("GEMINI_API_KEY", "").strip() or None
        return cls(
            gemini_api_key=api_key,
            generation_model=os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
            embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "768")),
            retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
            retrieval_min_score=float(os.getenv("RETRIEVAL_MIN_SCORE", "0.12")),
        )
