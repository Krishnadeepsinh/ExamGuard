"""Proctoring Agent contract for browser-classified events only."""

from __future__ import annotations

EVENT_IMPACTS = {
    "tab_switch": -8,
    "gaze_away": -5,
    "paste_detected": -10,
    "phone_detected": -20,
    "audio_spike": -3,
}


def behavioral_score(events: list[dict[str, object]]) -> float:
    score = 100
    for event in events:
        score += EVENT_IMPACTS.get(str(event.get("type")), 0)
    return max(0, min(100, score))
