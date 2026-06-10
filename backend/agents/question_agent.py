"""Question Generation Agent contract."""

from __future__ import annotations

from .bloom_templates import BLOOM_TEMPLATES, QUESTION_TYPE_SUFFIX


def build_prompt(level: str, question_type: str, context_chunks: list[str], marks: int) -> str:
    bloom = BLOOM_TEMPLATES[level]
    suffix = QUESTION_TYPE_SUFFIX[question_type]
    context = "\n\n".join(context_chunks)
    return (
        f"{bloom}\n"
        f"{suffix}\n"
        f"Marks: {marks}\n"
        "SOURCE-LOCK RULES:\n"
        "- Generate questions only from the source context below.\n"
        "- Do not use outside facts, general knowledge, web knowledge, or model memory.\n"
        "- If the source context is insufficient, return INSUFFICIENT_SOURCE instead of inventing a question.\n"
        "- Every generated question must include source page IDs and chunk IDs.\n"
        "- Reject questions whose answer cannot be verified directly from the source context.\n\n"
        f"Context:\n{context}"
    )


def groundedness_ok(score: float) -> bool:
    return score > 0.72
