"""Documented model routing table for every ExamGuard AI task."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    preferred: str
    fallback: str
    degraded: str
    user_message: str


ROUTES = {
    "question_generation": Route(
        preferred="gemini-1.5-flash",
        fallback="ollama:mistral:7b",
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
