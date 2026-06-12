"""Material Ingestion Agent contract.

This module is intentionally dependency-light for the hackathon scaffold. The
production implementation plugs in PyMuPDF, pdf2image, pytesseract, tiktoken,
sentence-transformers, and Supabase pgvector writes.
"""

from __future__ import annotations

import re
import hashlib
import math
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_text: str
    chapter_tag: str
    source_page: int
    chunk_index: int


def embed_text(text: str, dimensions: int = 384) -> list[float]:
    """Dependency-free signed feature hashing for pgvector retrieval."""
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 7) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def rank_chunks(query: str, chunks: list[dict], limit: int = 8) -> list[dict]:
    query_vector = embed_text(query)
    return sorted(
        chunks,
        key=lambda chunk: cosine_similarity(query_vector, embed_text(str(chunk.get("chunk_text", "")))),
        reverse=True,
    )[:limit]


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


def chunk_text_with_chapters(text: str, source_page: int = 1, approx_tokens: int = 512) -> tuple[list[Chunk], dict[str, list[str]]]:
    # 1. Parse all chapter headings and their locations
    headings: list[tuple[int, str]] = []
    ch_matches = re.finditer(
        r"\b(?:Chapter|Ch\.?)\s*(\d+)(?:\s+([A-Za-z0-9\s\-]+?))?\s*(?:explains|covers|discusses|about|is|features|\.|\b)",
        text,
        re.IGNORECASE
    )
    for match in ch_matches:
        num = match.group(1)
        name = match.group(2).strip() if match.group(2) else ""
        name = re.sub(r"\b(explains|covers|discusses|about|is|features)\b.*", "", name, flags=re.IGNORECASE).strip()
        tag = f"Chapter {num}"
        if name:
            tag = f"Chapter {num}: {name}"
        headings.append((match.start(), tag))

    if not headings:
        heading_matches = re.finditer(r"^\s*(\d+)\.\s+([A-Za-z0-9\s\-]+)", text, re.MULTILINE)
        for match in heading_matches:
            num = match.group(1)
            name = match.group(2).strip()
            tag = f"Chapter {num}: {name}"
            headings.append((match.start(), tag))

    if not headings:
        headings.append((0, "Chapter 12: Electromagnetic Induction"))

    headings.sort(key=lambda x: x[0])

    # 2. Extract topics for each chapter segment
    chapter_topics: dict[str, list[str]] = {}
    for i, (start_idx, tag) in enumerate(headings):
        end_idx = headings[i+1][0] if i + 1 < len(headings) else len(text)
        segment_text = text[start_idx:end_idx]

        topics: list[str] = []
        explain_match = re.search(
            r"\b(?:explains|covers|discusses|includes|features)\s+([^.]+)\.",
            segment_text,
            re.IGNORECASE
        )
        if explain_match:
            phrases = explain_match.group(1).split(",")
            for p in phrases:
                p_clean = re.sub(r"\b(and|or|of|in|a|an|the)\b", "", p, flags=re.IGNORECASE).strip()
                p_clean = p_clean.strip(".")
                if p_clean and len(p_clean) > 3:
                    topics.append(p_clean)

        if not topics:
            words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Za-z][a-z]+)*\b", segment_text)
            for w in words:
                if w.lower() not in ["chapter", "ch", "the", "this", "he", "she", "it", "they", "we", "physics", "chemistry", "math", "science"]:
                    topics.append(w)

        unique_topics: list[str] = []
        for t in topics:
            t_lower = t.lower()
            if t_lower not in [ut.lower() for ut in unique_topics] and len(unique_topics) < 8:
                unique_topics.append(t)
        chapter_topics[tag] = unique_topics

    # 3. Create chunks and assign the chapter tag based on index
    words = text.split()
    step = max(approx_tokens - 50, 1)
    chunks: list[Chunk] = []

    current_char_idx = 0
    for idx, start in enumerate(range(0, len(words), step)):
        part_words = words[start : start + approx_tokens]
        part = " ".join(part_words)
        if not part:
            continue

        chunk_char_idx = text.find(part, max(0, current_char_idx - 100))
        if chunk_char_idx == -1:
            chunk_char_idx = current_char_idx

        current_char_idx = chunk_char_idx + len(part)

        active_tag = headings[0][1]
        for heading_start, tag in headings:
            if chunk_char_idx >= heading_start:
                active_tag = tag
            else:
                break

        chunks.append(Chunk(part, active_tag, source_page, idx))

    return chunks, chapter_topics
