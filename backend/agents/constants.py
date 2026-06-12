"""Shared integrity constants for ExamGuard AI v6."""

from __future__ import annotations

from enum import StrEnum


class IntegrityStatus(StrEnum):
    CLEAN = "CLEAN"
    WATCH = "WATCH"
    WARN = "WARN"
    FLAGGED = "FLAGGED"


FACTOR_WEIGHTS = {
    "behavioral": 0.30,
    "perplexity": 0.15,
    "stylometric": 0.25,
    "answer_quality": 0.25,
    "time_anomaly": 0.05,
}

TIER3_WEIGHTS = {
    "behavioral": 0.38,
    "perplexity": 0.19,
    "answer_quality": 0.33,
    "time_anomaly": 0.10,
}

# Tier 2 has only 1-2 prior exams. Stylometric evidence remains available but
# is deliberately downweighted; the removed weight is redistributed across
# the four stronger signals. Weights sum to 1.00.
TIER2_WEIGHTS = {
    "behavioral": 0.35,
    "perplexity": 0.17,
    "stylometric": 0.10,
    "answer_quality": 0.32,
    "time_anomaly": 0.06,
}


def status_for_score(score: float) -> IntegrityStatus:
    """Unified v6 thresholds used by UI, API, tests, reports, and demo."""
    if score > 85:
        return IntegrityStatus.CLEAN
    if score >= 70:
        return IntegrityStatus.WATCH
    if score >= 50:
        return IntegrityStatus.WARN
    return IntegrityStatus.FLAGGED


def confidence_interval_for_tier(tier: int) -> int | None:
    if tier == 1:
        return 7
    if tier == 2:
        return 15
    return None
