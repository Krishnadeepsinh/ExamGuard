"""Gemini-only model routing with backend-side key rotation."""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from backend.config import settings


@dataclass(frozen=True)
class Route:
    preferred: str
    fallback: str
    degraded: str
    user_message: str


ROUTES = {
    "question_generation": Route(
        preferred="gemini-2.5-flash",
        fallback="next_gemini_key",
        degraded="cached_question_pool",
        user_message="Using cached questions because generation queue is busy.",
    ),
    "answer_evaluation": Route(
        preferred="gemini-1.5-flash",
        fallback="ollama:mistral:7b",
        degraded="manual_review_required",
        user_message="AI evaluation unavailable; teacher review required.",
    ),
    "report_summary": Route(
        preferred="gemini-1.5-flash",
        fallback="ollama:mistral:7b",
        degraded="template_report",
        user_message="Report generated with data-only summary.",
    ),
    "ai_cheat_scoring": Route(
        preferred="ollama_logprobs",
        fallback="sliding_window_entropy",
        degraded="four_factor_score",
        user_message="Perplexity signal unavailable; other integrity signals active.",
    ),
    "stylometric_scoring": Route(
        preferred="sentence_transformers",
        fallback="tfidf_cosine",
        degraded="tier3_disabled",
        user_message="Stylometric signal unavailable for this session.",
    ),
    "ocr": Route(
        preferred="pytesseract",
        fallback="google_vision_api",
        degraded="manual_text_paste",
        user_message="Auto-OCR failed. Please paste text manually.",
    ),
}


def route_for(task: str) -> Route:
    return ROUTES[task]


class GeminiRouter:
    """Rotate keys without ever exposing key values outside this module."""

    def __init__(self, keys: tuple[str, ...] | None = None, model: str | None = None) -> None:
        self.keys = keys if keys is not None else settings.gemini_api_keys
        self.model = model or settings.gemini_model
        self._index = 0
        self._lock = threading.Lock()
        self._cooldown_until: dict[int, float] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.keys)

    def status(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "provider": "gemini", "model": self.model, "key_count": len(self.keys)}

    def _ordered_indices(self) -> list[int]:
        with self._lock:
            start = self._index % max(1, len(self.keys))
            self._index = (start + 1) % max(1, len(self.keys))
        return [(start + offset) % len(self.keys) for offset in range(len(self.keys))]

    def generate(self, prompt: str, *, timeout: int = 45) -> str:
        if not self.keys:
            raise RuntimeError("Gemini is not configured")
        last_error = "all Gemini keys failed"
        now = time.monotonic()
        for index in self._ordered_indices():
            if self._cooldown_until.get(index, 0) > now:
                continue
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.25,
                    "responseMimeType": "application/json",
                    "maxOutputTokens": 8192,
                },
            }).encode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            req = request.Request(url, data=payload, method="POST", headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.keys[index],
            })
            try:
                with request.urlopen(req, timeout=timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return body["candidates"][0]["content"]["parts"][0]["text"]
            except error.HTTPError as exc:
                last_error = f"Gemini HTTP {exc.code}"
                self._cooldown_until[index] = now + (300 if exc.code in {400, 401, 403} else 60)
            except (error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
                last_error = f"Gemini request failed: {type(exc).__name__}"
                self._cooldown_until[index] = now + 30
        raise RuntimeError(last_error)


def parse_question_json(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("questions", [])
    if not isinstance(data, list):
        raise ValueError("Gemini response must be a question array")
    return [item for item in data if isinstance(item, dict) and str(item.get("text", "")).strip()]


def question_quality_errors(question: dict[str, Any], question_type: str) -> list[str]:
    """Reject malformed, source-leaking, or low-value generated questions."""
    errors: list[str] = []
    text = str(question.get("text", "")).strip()
    answer = str(question.get("correct_answer", "")).strip()
    options = question.get("options") or []
    lowered = text.lower()
    meta_patterns = (
        r"\baccording to\b",
        r"\b(?:uploaded|provided|given)\s+(?:syllabus|material|document|text|passage|source)\b",
        r"\b(?:syllabus|material|document|passage|source)\s+(?:says|states|mentions|covers|includes|describes)\b",
        r"\bwhat (?:does|is) (?:the )?(?:syllabus|material|document|passage|source)\b",
        r"\bwhich (?:topic|concept|chapter)\b.*\b(?:covered|included|mentioned|listed)\b",
        r"\b(?:this|the)\s+(?:chapter|section|passage|document)\b",
        r"\bsource\s*\d+\b",
        r"\bpage\s*\d+\b",
    )
    if len(text) < 18 or not text.endswith(("?", ".")):
        errors.append("question text is incomplete")
    if any(re.search(pattern, lowered) for pattern in meta_patterns):
        errors.append("question refers to source material")
    if not answer:
        errors.append("answer or marking guide is missing")
    if question_type == "MCQ":
        if not isinstance(options, list) or len(options) != 4:
            errors.append("MCQ must contain exactly four options")
        elif len({str(option).strip().casefold() for option in options}) != 4:
            errors.append("MCQ options must be distinct")
        elif answer not in options:
            errors.append("MCQ answer must exactly match one option")
    elif question_type == "Fill Blank" and "_____" not in text:
        errors.append("fill-blank question needs one blank")
    elif question_type == "True/False" and answer.casefold() not in {"true", "false"}:
        errors.append("true/false answer must be True or False")
    return errors


gemini_router = GeminiRouter()


def generate_grounded_questions(
    question_type: str,
    count: int,
    level: str,
    bloom: str,
    marks_each: int,
    source_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    excerpts = "\n\n".join(
        f"SOURCE {i + 1} [{chunk.get('id', chunk.get('chunk_index', i))}]: {chunk.get('chunk_text', '')[:1800]}"
        for i, chunk in enumerate(source_chunks[:8])
    )
    source_count = max(1, min(len(source_chunks), 8))
    coverage_plan = ", ".join(
        f"question {index + 1} -> SOURCE {(index % source_count) + 1}"
        for index in range(count)
    )
    prompt = f"""Create exactly {count} {question_type} exam questions.
Difficulty: {level}. Bloom level: {bloom}. Marks each: {marks_each}.
Use each assigned source only as factual grounding. Write normal subject-concept exam questions for a student who never sees the source.
Coverage plan: {coverage_plan}.
For every item, source_number must equal its assigned SOURCE number from the coverage plan.
Never ask what the document, source, syllabus, chapter list, passage, or uploaded material says, covers, includes, mentions, or describes.
Never ask which topic/chapter/concept appears in the source. Ask directly about the underlying subject concept instead.
Do not copy source sentences as questions. Test understanding, application, or analysis of concepts.
Every question must be self-contained, unambiguous, grammatically complete, and distinct from every other question.
Match difficulty and Bloom level through reasoning depth, not obscure wording.
For MCQ: provide one unquestionably correct answer and three plausible same-category distractors. No joke, meta, or obviously false distractors.
For subjective questions: ask a direct task and provide a concise marking guide containing expected key points.
Never include source labels, page numbers, raw excerpts, quotation marks around source text, or phrases such as "according to the material".
Avoid duplicate concepts unless different sections explicitly require different Bloom-level treatment.
Return JSON array only. Each item: {{"text":"...","options":[],"correct_answer":"...","source_number":1}}.
For MCQ, options must contain exactly 4 plain strings and correct_answer must exactly match one option.
For Fill Blank, include one clear blank as _____. For True/False, correct_answer must be True or False.
For subjective questions, correct_answer is a concise marking guide grounded in source.

SOURCE MATERIAL:
{excerpts}
"""
    last_errors: list[str] = []
    for attempt in range(2):
        retry_note = "" if attempt == 0 else f"\nPrevious response failed validation: {'; '.join(last_errors)}. Repair every issue."
        questions = parse_question_json(gemini_router.generate(prompt + retry_note))
        last_errors = []
        if len(questions) != count:
            last_errors.append(f"returned {len(questions)} questions; expected {count}")
        normalized_texts: set[str] = set()
        for index, question in enumerate(questions):
            errors = question_quality_errors(question, question_type)
            expected_source = (index % source_count) + 1
            try:
                actual_source = int(question.get("source_number", 0))
            except (TypeError, ValueError):
                actual_source = 0
            if actual_source != expected_source:
                errors.append(f"source_number must be {expected_source}")
            normalized = " ".join(str(question.get("text", "")).casefold().split())
            if normalized in normalized_texts:
                errors.append("duplicate question")
            normalized_texts.add(normalized)
            last_errors.extend(f"question {index + 1}: {error}" for error in errors)
        if not last_errors:
            return questions
    raise ValueError("Gemini question quality validation failed: " + "; ".join(last_errors[:8]))
