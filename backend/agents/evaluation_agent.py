"""Evaluation Agent contract."""

from __future__ import annotations

from difflib import SequenceMatcher


def grade_objective(answer: str, correct_answer: str, marks: int) -> dict[str, object]:
    ratio = SequenceMatcher(None, answer.strip().lower(), correct_answer.strip().lower()).ratio()
    score = marks if ratio > 0.86 else 0
    return {"score": score, "reasoning": "deterministic objective grading", "similarity": round(ratio, 2)}
