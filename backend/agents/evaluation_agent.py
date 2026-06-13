"""Evaluation Agent contract."""

from __future__ import annotations

from difflib import SequenceMatcher
import re


def grade_objective(answer: str, correct_answer: str, marks: int) -> dict[str, object]:
    ratio = SequenceMatcher(None, answer.strip().lower(), correct_answer.strip().lower()).ratio()
    score = marks if ratio > 0.86 else 0
    return {"score": score, "reasoning": "deterministic objective grading", "similarity": round(ratio, 2)}


def grade_subjective(answer: str, marking_guide: str, marks: int) -> dict[str, object]:
    """Transparent marking-guide overlap fallback when live LLM rubric grading is unavailable."""
    words = lambda text: {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 3}
    expected = words(marking_guide)
    supplied = words(answer)
    coverage = len(expected & supplied) / max(1, len(expected))
    completeness = min(1.0, len(answer.split()) / max(20, marks * 8))
    ratio = min(1.0, coverage * 0.75 + completeness * 0.25)
    score = round(marks * ratio, 2)
    return {"score": score, "reasoning": "marking-guide concept coverage", "similarity": round(ratio, 2)}
