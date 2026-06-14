"""Evaluation Agent contract."""

from __future__ import annotations

from difflib import SequenceMatcher
import re


def _normalize_objective(text: str) -> str:
    value = re.sub(r"\s+", " ", text.strip().lower())
    value = re.sub(r"^[\(\[]?[a-d1-4][\)\].:-]\s+", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _option_text(label: str, options: list[str]) -> str | None:
    cleaned = label.strip().lower().rstrip(".):")
    if cleaned in {"a", "b", "c", "d"}:
        index = ord(cleaned) - ord("a")
    elif cleaned in {"1", "2", "3", "4"}:
        index = int(cleaned) - 1
    else:
        return None
    return options[index] if 0 <= index < len(options) else None


def grade_objective(answer: str, correct_answer: str, marks: int, options: list[str] | None = None) -> dict[str, object]:
    """Grade objective answers while tolerating option labels and option text.

    Generated papers may store the answer key as either the option text or a
    label such as "B". Student submissions may likewise save the label or the
    selected option text. Treat those equivalent forms as exact matches.
    """
    options = options or []
    answer_variants = {answer, _normalize_objective(answer)}
    correct_variants = {correct_answer, _normalize_objective(correct_answer)}
    mapped_answer = _option_text(answer, options)
    mapped_correct = _option_text(correct_answer, options)
    if mapped_answer:
        answer_variants.add(mapped_answer)
        answer_variants.add(_normalize_objective(mapped_answer))
    if mapped_correct:
        correct_variants.add(mapped_correct)
        correct_variants.add(_normalize_objective(mapped_correct))
    normalized_answers = {_normalize_objective(item) for item in answer_variants if item}
    normalized_correct = {_normalize_objective(item) for item in correct_variants if item}
    exact = bool(normalized_answers & normalized_correct)
    ratio = max(
        (SequenceMatcher(None, item, expected).ratio() for item in normalized_answers for expected in normalized_correct),
        default=0,
    )
    score = marks if exact or ratio > 0.92 else 0
    return {"score": score, "reasoning": "deterministic objective grading", "similarity": round(ratio, 2)}


STOP_WORDS = {
    "about", "after", "again", "also", "because", "been", "before", "being", "between",
    "could", "does", "each", "from", "have", "into", "more", "most", "other", "should",
    "than", "that", "their", "there", "these", "they", "this", "through", "using", "very",
    "what", "when", "where", "which", "while", "with", "would",
}


def _concepts(text: str) -> set[str]:
    concepts: set[str] = set()
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) <= 3 or word in STOP_WORDS:
            continue
        # A light deterministic stem keeps common plurals/verb forms comparable.
        for suffix in ("ingly", "edly", "ation", "ments", "ment", "ing", "ed", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                word = word[:-len(suffix)]
                break
        concepts.add(word)
    return concepts


def grade_subjective(answer: str, marking_guide: str, marks: int, question_type: str = "Short Answer") -> dict[str, object]:
    """Deterministic rubric grading for brief, long, and essay answers.

    The score combines required-concept coverage, answer relevance, and expected
    development. Length can improve a relevant answer, but cannot earn marks on
    its own. The component values are returned for auditability.
    """
    supplied_text = answer.strip()
    if not supplied_text:
        return {"score": 0, "reasoning": "blank subjective answer", "similarity": 0, "rubric": {}}

    expected = _concepts(marking_guide)
    supplied = _concepts(supplied_text)
    overlap = expected & supplied
    coverage = len(overlap) / max(1, len(expected))
    relevance = len(overlap) / max(1, len(supplied | expected))
    phrase_similarity = SequenceMatcher(None, supplied_text.lower(), marking_guide.strip().lower()).ratio()
    expected_words = max(12, marks * (14 if question_type in {"Long Answer", "Essay"} else 7))
    completeness = min(1.0, len(supplied_text.split()) / expected_words)

    if not overlap and phrase_similarity < 0.18:
        ratio = 0.0
    else:
        ratio = min(1.0, coverage * 0.58 + relevance * 0.17 + phrase_similarity * 0.15 + completeness * 0.10)
    score = round(marks * ratio, 2)
    rubric = {
        "concept_coverage": round(coverage, 3),
        "relevance": round(relevance, 3),
        "answer_similarity": round(phrase_similarity, 3),
        "development": round(completeness, 3),
        "matched_concepts": sorted(overlap),
    }
    return {
        "score": score,
        "reasoning": (
            f"deterministic {question_type.lower()} rubric: "
            f"concepts {rubric['concept_coverage']}, relevance {rubric['relevance']}, "
            f"development {rubric['development']}"
        ),
        "similarity": round(ratio, 3),
        "rubric": rubric,
    }
