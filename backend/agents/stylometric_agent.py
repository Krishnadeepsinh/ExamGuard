"""Stylometric Agent tier strategy."""

from __future__ import annotations


def tier_for_baseline_count(count: int) -> int:
    if count >= 3:
        return 1
    if count >= 1:
        return 2
    return 3


def stylometric_payload(baseline_count: int, style_distance: float | None) -> dict[str, object]:
    tier = tier_for_baseline_count(baseline_count)
    if tier == 3:
        return {
            "baseline_tier": 3,
            "stylometric_score": None,
            "message": "First exam: stylometric analysis unavailable; baseline is being built.",
        }
    score = max(0, min(100, 100 - ((style_distance or 0) * 100)))
    return {
        "baseline_tier": tier,
        "stylometric_score": round(score, 2),
        "ci": 7 if tier == 1 else 15,
    }
