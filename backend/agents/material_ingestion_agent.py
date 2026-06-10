"""Material Ingestion Agent contract.

This module is intentionally dependency-light for the hackathon scaffold. The
production implementation plugs in PyMuPDF, pdf2image, pytesseract, tiktoken,
sentence-transformers, and Supabase pgvector writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_text: str
    chapter_tag: str
    source_page: int
    chunk_index: int


CHAPTER_PATTERN = re.compile(r"\b(?:chapter|ch\.?)\s*(\d+)|^\s*(\d{1,2})\.\s+", re.IGNORECASE)


def detect_chapter(text: str, fallback: str = "unknown") -> str:
    match = CHAPTER_PATTERN.search(text)
    number = match.group(1) or match.group(2) if match else None
    return f"Ch {number}" if number else fallback


def chunk_text(text: str, source_page: int = 1, approx_tokens: int = 512) -> list[Chunk]:
    words = text.split()
    step = max(approx_tokens - 50, 1)
    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(words), step)):
        part = " ".join(words[start : start + approx_tokens])
        if part:
            chunks.append(Chunk(part, detect_chapter(part), source_page, index))
    return chunks
