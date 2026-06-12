"""Deterministic Orchestrator Agent for v6 integrity scoring."""

from __future__ import annotations

from .constants import FACTOR_WEIGHTS, TIER2_WEIGHTS, TIER3_WEIGHTS, confidence_interval_for_tier, status_for_score


def compute_integrity_score(factors: dict[str, float], baseline_tier: int) -> dict[str, object]:
    if baseline_tier == 3:
        score = (
            factors["behavioral"] * TIER3_WEIGHTS["behavioral"]
            + factors["perplexity"] * TIER3_WEIGHTS["perplexity"]
            + factors["answer_quality"] * TIER3_WEIGHTS["answer_quality"]
            + factors["time_anomaly"] * TIER3_WEIGHTS["time_anomaly"]
        )
    elif baseline_tier == 2:
        score = sum(factors[name] * weight for name, weight in TIER2_WEIGHTS.items())
    else:
        score = sum(factors[name] * weight for name, weight in FACTOR_WEIGHTS.items())

    rounded = round(score, 2)
    status = status_for_score(rounded)
    return {
        "score": rounded,
        "status": status.value,
        "ci": confidence_interval_for_tier(baseline_tier),
        "baseline_tier": baseline_tier,
        "factors": factors,
        "decision_source": "deterministic_orchestrator",
    }
