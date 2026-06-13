"""Proctoring Agent contract for browser-classified events only."""

from __future__ import annotations

EVENT_IMPACTS = {
    "tab_switch": -8,
    "tab_hidden": -8,
    "window_blur": -2,
    "fullscreen_exit": -6,
    "gaze_away": -2,
    "paste_detected": -4,
    "right_click": 0,
    "phone_detected": -20,
    "audio_spike": -1,
    "face_missing": -4,
    "multiple_faces": -12,
    "monitoring_interrupted": -3,
}


def impact_for(event_type: str, metadata: dict[str, object] | None = None) -> int:
    metadata = metadata or {}
    if event_type == "paste_detected":
        return -12 if metadata.get("bulk_paste") is True else 0
    return EVENT_IMPACTS.get(event_type, 0)


def behavioral_score(events: list[dict[str, object]]) -> float:
    score = 100
    for event in events:
        score += impact_for(str(event.get("type")), event.get("metadata") if isinstance(event.get("metadata"), dict) else {})
    return max(0, min(100, score))


def has_critical_pattern(events: list[dict[str, object]]) -> bool:
    """Escalate only repeated, multi-vector behavior; one accidental event never flags."""
    types = [str(event.get("type")) for event in events]
    tab_events = types.count("tab_hidden") + types.count("tab_switch")
    bulk_pastes = sum(
        event.get("type") == "paste_detected"
        and isinstance(event.get("metadata"), dict)
        and event["metadata"].get("bulk_paste") is True
        for event in events
    )
    presence_events = types.count("face_missing") + (types.count("multiple_faces") * 2)
    independent_vectors = sum((bulk_pastes > 0, "fullscreen_exit" in types, "phone_detected" in types, presence_events >= 2))
    return (tab_events >= 3 and independent_vectors >= 1) or independent_vectors >= 2
