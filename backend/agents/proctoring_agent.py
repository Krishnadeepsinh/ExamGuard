"""Proctoring Agent contract for browser-classified events only."""

from __future__ import annotations

EVENT_IMPACTS = {
    "tab_switch": -20,
    "tab_hidden": -20,
    "window_blur": -5,
    "fullscreen_exit": -10,
    "gaze_away": -5,
    "paste_detected": -20,
    "right_click": -3,
    "phone_detected": -20,
    "audio_spike": -3,
}


def impact_for(event_type: str) -> int:
    return EVENT_IMPACTS.get(event_type, 0)


def behavioral_score(events: list[dict[str, object]]) -> float:
    score = 100
    for event in events:
        score += EVENT_IMPACTS.get(str(event.get("type")), 0)
    return max(0, min(100, score))
