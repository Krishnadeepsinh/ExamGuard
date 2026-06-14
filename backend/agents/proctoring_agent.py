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


def _signal_category(event: dict[str, object]) -> str | None:
    event_type = str(event.get("type"))
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    if event_type in {"tab_switch", "tab_hidden", "window_blur", "fullscreen_exit"}:
        return "focus"
    if event_type == "paste_detected" and metadata.get("bulk_paste") is True:
        return "content"
    if event_type in {"face_missing", "multiple_faces"}:
        return "presence"
    if event_type == "phone_detected":
        return "device"
    if event_type == "monitoring_interrupted" and metadata.get("reason") != "camera_or_detector_unavailable":
        return "monitoring"
    return None


def integrity_warning_count(events: list[dict[str, object]]) -> int:
    """Return 0-4 graduated warnings while ignoring weak one-off noise."""
    categorized = [category for event in events if (category := _signal_category(event)) is not None]
    if not categorized:
        return 0
    categories = len(set(categorized))
    meaningful = len(categorized)
    has_device = "device" in categorized
    if has_device and categories >= 3 and meaningful >= 5:
        return 4
    if has_device and categories >= 2 and meaningful >= 3:
        return 3
    if categories >= 3 and meaningful >= 6:
        return 4
    if categories >= 2 and meaningful >= 4:
        return 3
    if categories >= 2 or meaningful >= 3:
        return 2
    return 1


def has_critical_pattern(events: list[dict[str, object]]) -> bool:
    """Require corroborated evidence across three independent vectors before a hold."""
    categorized = [category for event in events if (category := _signal_category(event)) is not None]
    categories = set(categorized)
    has_strong_evidence = any(
        str(event.get("type")) in {"phone_detected", "multiple_faces"}
        or (event.get("type") == "paste_detected" and isinstance(event.get("metadata"), dict) and event["metadata"].get("bulk_paste") is True)
        for event in events
    )
    repeated_category = any(categorized.count(category) >= 2 for category in categories)
    if "device" in categories and len(categories) >= 3 and len(categorized) >= 5 and has_strong_evidence:
        return True
    return len(categories) >= 3 and len(categorized) >= 7 and has_strong_evidence and repeated_category
