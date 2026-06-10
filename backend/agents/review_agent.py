"""Review Agent appeal state machine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def open_appeal(session_id: str) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "session_id": session_id,
        "review_status": "awaiting_response",
        "deadline_at": (now + timedelta(hours=24)).isoformat(),
        "student_summary": "Some answer patterns require teacher review. No final decision has been made.",
    }


def decide(session_id: str, decision: str, teacher_id: str) -> dict[str, object]:
    if decision not in {"cleared", "confirmed_flag"}:
        raise ValueError("decision must be cleared or confirmed_flag")
    return {
        "session_id": session_id,
        "teacher_id": teacher_id,
        "teacher_decision": decision,
        "review_status": "decided",
        "grade_released": True,
        "decision_at": datetime.now(timezone.utc).isoformat(),
    }
