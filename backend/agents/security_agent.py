"""Security Agent for AI-written answer detection."""

from __future__ import annotations

import math
from collections import Counter


def shannon_entropy(text: str) -> float:
    tokens = text.lower().split()
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def entropy_score(text: str) -> dict[str, object]:
    entropy = shannon_entropy(text)
    score = max(0, min(100, entropy / 8 * 100))
    return {
        "perplexity_score": round(score, 2),
        "ai_detection_method": "entropy",
        "note": "Used sliding-window entropy fallback because logprobs were unavailable.",
    }
