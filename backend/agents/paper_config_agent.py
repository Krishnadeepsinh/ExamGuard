"""Paper Config Agent.

Validates marks, chapter coverage, and join-code readiness before generation.
"""

from __future__ import annotations

import random
import string
from typing import Any

ALLOWED_QUESTION_TYPES = {"MCQ", "Short Answer", "Long Answer", "Fill Blank", "True/False", "Essay"}
ALLOWED_LEVELS = {"Easy", "Standard", "Challenging"}
ALLOWED_MODES = {"MCQ only", "MCQ + QA", "Mixed"}
MODE_TYPES = {
    "MCQ only": {"MCQ"},
    "MCQ + QA": {"MCQ", "Short Answer", "Long Answer", "Essay"},
    "Mixed": ALLOWED_QUESTION_TYPES,
}


def generate_join_code(existing_codes: set[str] | None = None) -> str:
    existing_codes = existing_codes or set()
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(alphabet) for _ in range(6))
        if code not in existing_codes:
            return code


def validate_paper_config(config: dict[str, Any], chapter_chunk_counts: dict[str, int]) -> dict[str, Any]:
    total_marks = int(config["total_marks"])
    sections = config["sections"]
    paper_mode = config.get("paper_mode", "Mixed")
    overall_level = config.get("overall_level", "Standard")
    material_id = config.get("material_id")
    actual = sum(int(section["count"]) * int(section["marks_each"]) for section in sections)
    errors: list[str] = []

    if not material_id:
        errors.append("Upload syllabus material before configuring or generating the paper.")

    if paper_mode not in ALLOWED_MODES:
        errors.append(f"Unsupported paper mode: {paper_mode}.")

    if overall_level not in ALLOWED_LEVELS:
        errors.append(f"Unsupported overall difficulty level: {overall_level}.")

    if actual != total_marks:
        errors.append(f"Marks budget invalid: currently {actual}/{total_marks} marks.")

    for section in sections:
        question_type = section.get("type")
        section_level = section.get("level", overall_level)
        if question_type not in ALLOWED_QUESTION_TYPES:
            errors.append(f"Unsupported question type: {question_type}.")
        if paper_mode in MODE_TYPES and question_type not in MODE_TYPES[paper_mode]:
            errors.append(f"{question_type} is not allowed for {paper_mode} paper mode.")
        if section_level not in ALLOWED_LEVELS:
            errors.append(f"Unsupported section difficulty level: {section_level}.")
        if int(section["count"]) < 1 or int(section["marks_each"]) < 1:
            errors.append("Each section needs at least one question and one mark per question.")

        chapter = section.get("chapter_tag")
        if not chapter:
            errors.append("Every section must choose a chapter/source area.")
            continue
            
        if material_id:
            # Short syllabus PDFs may only produce a few dense 384-token chunks.
            # One verified source chunk is enough to keep generation grounded;
            # diversity is handled later by retrieval/ranking and citations.
            needed = 1
            available = chapter_chunk_counts.get(chapter, 0)
            if available < needed:
                errors.append(f"Not enough material in {chapter}: need {needed} chunks, have {available}.")

    return {
        "status": "config_validated" if not errors else "invalid",
        "errors": errors,
        "join_code": generate_join_code() if not errors else None,
        "estimated_seconds": min((sum(int(s["count"]) for s in sections) * 8) + (len(sections) * 5), 600),
    }
