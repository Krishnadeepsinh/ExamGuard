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


def balanced_rank_chunks(query: str, chunks: list[dict], limit: int = 8, chapter_offset: int = 0) -> list[dict]:
    """Rank chunks while preserving chapter coverage.

    Global similarity ranking tends to select several chunks from the same
    chapter. For whole-syllabus generation, rotate through chapter groups and
    take the best remaining chunk from each group before taking a second chunk
    from any chapter.
    """
    if limit <= 0 or not chunks:
        return []
    grouped: dict[str, list[dict]] = {}
    for chunk in chunks:
        tag = str(chunk.get("chapter_tag") or "Complete source")
        grouped.setdefault(tag, []).append(chunk)

    def chapter_key(tag: str) -> tuple[int, str]:
        match = re.search(r"\d+", tag)
        return (int(match.group()) if match else 10**9, tag.casefold())

    tags = sorted(grouped, key=chapter_key)
    if not tags:
        return rank_chunks(query, chunks, limit)
    rotation = chapter_offset % len(tags)
    tags = tags[rotation:] + tags[:rotation]
    ranked = {tag: rank_chunks(query, grouped[tag], len(grouped[tag])) for tag in tags}
    selected: list[dict] = []
    depth = 0
    while len(selected) < limit:
        added = False
        for tag in tags:
            candidates = ranked[tag]
            if depth < len(candidates):
                selected.append(candidates[depth])
                added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        depth += 1
    return selected


CHAPTER_PATTERN = re.compile(r"\b(?:chapter|ch\.?)\s*(\d+)|^\s*(\d{1,2})\.\s+", re.IGNORECASE)


def detect_chapter(text: str, fallback: str = "unknown") -> str:
    match = CHAPTER_PATTERN.search(text)
    number = match.group(1) or match.group(2) if match else None
    return f"Ch {number}" if number else fallback


def chunk_text(text: str, source_page: int = 1, approx_tokens: int = 512) -> list[Chunk]:
    words = text.split()
    overlap = min(50, max(1, approx_tokens // 8))
    step = max(approx_tokens - overlap, 1)
    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(words), step)):
        part = " ".join(words[start : start + approx_tokens])
        if part:
            chunks.append(Chunk(part, detect_chapter(part), source_page, index))
    return chunks


def _heading_from_line(line: str) -> tuple[str, str] | None:
    cleaned = " ".join(line.strip().split())
    if not cleaned or len(cleaned) > 160:
        return None
    patterns = (
        (r"^(chapter|ch\.?)\s*([0-9]+|[ivxlcdm]+)\s*[:.\-]?\s*(.*)$", "Chapter"),
        (r"^(unit)\s*([0-9]+|[ivxlcdm]+)\s*[:.\-]?\s*(.*)$", "Unit"),
        (r"^([0-9]{1,3})[.)]\s+(.{3,120})$", "Chapter"),
    )
    for pattern, label in patterns:
        match = re.match(pattern, cleaned, re.IGNORECASE)
        if not match:
            continue
        if label == "Chapter" and len(match.groups()) == 3:
            number, title = match.group(2), match.group(3)
        elif label == "Unit":
            number, title = match.group(2), match.group(3)
        else:
            number, title = match.group(1), match.group(2)
        title = re.sub(r"\s+\.{2,}\s*\d+\s*$", "", title).strip(" .:-")
        tag = f"{label} {number.upper() if not number.isdigit() else number}"
        return tag, title
    return None


def _chapter_headings(text: str) -> list[tuple[int, str]]:
    lines = list(re.finditer(r"^.*$", text, re.MULTILINE))
    headings: list[tuple[int, str]] = []
    for index, line_match in enumerate(lines):
        parsed = _heading_from_line(line_match.group())
        if not parsed:
            continue
        tag, title = parsed
        if not title:
            for next_line in lines[index + 1:index + 3]:
                candidate = " ".join(next_line.group().strip().split())
                if candidate and len(candidate) <= 120 and not _heading_from_line(candidate):
                    title = candidate.strip(" .:-")
                    break
        headings.append((line_match.start(), f"{tag}: {title}" if title else tag))

    if headings:
        return headings

    # Plain-text syllabus exports sometimes place all chapter labels inline.
    for match in re.finditer(
        r"\b(Chapter|Ch\.?|Unit)\s*([0-9]+|[ivxlcdm]+)\s*[:.\-]?\s*([^\n.;]{0,100})",
        text,
        re.IGNORECASE,
    ):
        label = "Unit" if match.group(1).lower().startswith("unit") else "Chapter"
        number = match.group(2)
        title = re.sub(r"\b(explains|covers|discusses|includes|features)\b.*", "", match.group(3), flags=re.IGNORECASE).strip(" .:-")
        tag = f"{label} {number.upper() if not number.isdigit() else number}"
        headings.append((match.start(), f"{tag}: {title}" if title else tag))
    return headings


def _segment_topics(tag: str, segment: str) -> list[str]:
    topics: list[str] = []
    title = tag.split(":", 1)[1].strip() if ":" in tag else ""
    if title:
        topics.append(title)
    for match in re.finditer(r"\b(?:covers|includes|topics?|concepts?)\s*(?:include|are|:)?\s*([^.\n]+)", segment, re.IGNORECASE):
        for phrase in re.split(r",|;|\band\b", match.group(1), flags=re.IGNORECASE):
            cleaned = " ".join(phrase.strip(" .:-").split())
            if 3 < len(cleaned) <= 80:
                topics.append(cleaned)
    unique: list[str] = []
    for topic in topics:
        if topic.casefold() not in {item.casefold() for item in unique}:
            unique.append(topic)
        if len(unique) == 8:
            break
    return unique


def chunk_text_with_chapters(text: str, source_page: int = 1, approx_tokens: int = 512) -> tuple[list[Chunk], dict[str, list[str]]]:
    headings = sorted(_chapter_headings(text), key=lambda item: item[0])
    if not headings:
        headings = [(0, "Complete source")]

    segments: list[tuple[str, str]] = []
    if headings[0][0] > 0 and len(text[:headings[0][0]].split()) >= 20:
        segments.append(("Complete source", text[:headings[0][0]]))
    for index, (start, tag) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        segment = text[start:end].strip()
        if segment:
            segments.append((tag, segment))

    chunks: list[Chunk] = []
    chapter_topics: dict[str, list[str]] = {}
    overlap = min(50, max(1, approx_tokens // 8))
    step = max(approx_tokens - overlap, 1)
    for tag, segment in segments:
        chapter_topics[tag] = _segment_topics(tag, segment)
        words = segment.split()
        for start in range(0, len(words), step):
            part = " ".join(words[start:start + approx_tokens]).strip()
            if part:
                chunks.append(Chunk(part, tag, source_page, len(chunks)))
    return chunks, chapter_topics
