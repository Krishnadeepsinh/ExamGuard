"""Seed a demo-ready ExamGuard AI v6 environment.

This script is intentionally safe and dry-run friendly in the scaffold. Wire the
helper functions to Supabase once credentials are available.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


DEMO = {
    "teacher": "teacher@demo.examguard.ai / demo123",
    "students": [
        "arjun@student.ai / demo123 (CLEAN, Tier 1, score 88)",
        "priya@student.ai / demo123 (FLAGGED, Tier 1, score 43)",
        "rahul@student.ai / demo123 (WARN, Tier 3, score 65)",
    ],
    "join_code": "ABC123",
    "exam": "Physics XI - Electromagnetism",
}


def warmup_ollama() -> None:
    print("Step 0: warmup Fly.io Ollama endpoint")
    time.sleep(0.2)
    print("  ok: warmup simulated")


def main() -> None:
    warmup_ollama()
    steps = [
        "create teacher",
        "create 3 students with baseline tiers",
        "create Physics exam",
        "upload NCERT Physics PDF",
        "configure 6-section 80-mark paper",
        "generate grounded questions",
        "create clean, flagged, and warn sessions",
        "generate reports",
        "print demo credentials",
    ]
    for index, step in enumerate(steps, start=1):
        print(f"Step {index}: {step}")
        time.sleep(0.05)

    output = Path("demo/demo_ready.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(DEMO, indent=2), encoding="utf-8")
    print("\nEXAMGUARD AI DEMO READY")
    print(f"Teacher: {DEMO['teacher']}")
    for student in DEMO["students"]:
        print(f"Student: {student}")
    print(f"Join code: {DEMO['join_code']}")
    print("Frontend: http://localhost:5173")


if __name__ == "__main__":
    main()
