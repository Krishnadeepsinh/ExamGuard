"""Report Agent scaffold."""

from __future__ import annotations


def report_outline(session_id: str) -> list[str]:
    return [
        f"Summary for session {session_id}",
        "IntegrityScoreCard with confidence interval and baseline tier",
        "Behavioral event timeline",
        "Per-question answer and source citation analysis",
        "Appeal section and teacher decision audit trail",
    ]
