"""Smoke test the local ExamGuard API core flow."""

from __future__ import annotations

import json
from urllib import request


BASE = "http://127.0.0.1:8000/api/v1"


def call(method: str, path: str, payload: dict | None = None) -> dict | list:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    login = call("POST", "/auth/login", {
        "email": "teacher@demo.examguard.ai",
        "password": "demo123",
        "role": "teacher",
        "display_name": "Rajan Kumar",
    })
    exam = call("GET", f"/exams?teacher_id={login['user']['id']}")[0]
    material = call("GET", f"/exams/{exam['id']}/materials")[0]
    config = {
        "material_id": material["id"],
        "total_marks": 20,
        "overall_level": "Standard",
        "paper_mode": "Mixed",
        "sections": [
            {"id": "A", "type": "MCQ", "count": 2, "marks_each": 5, "bloom": "Understand", "chapter_tag": "Chapter 12: Electromagnetic", "level": "Use overall"},
            {"id": "B", "type": "Short Answer", "count": 2, "marks_each": 5, "bloom": "Analyze", "chapter_tag": "Chapter 13: Alternating", "level": "Challenging"},
        ],
    }
    call("PUT", f"/exams/{exam['id']}/paper-config", config)
    generated = call("POST", f"/exams/{exam['id']}/generate")
    call("POST", f"/exams/{exam['id']}/activate")
    session = call("POST", "/sessions/join", {"join_code": exam["join_code"], "student_name": "Arjun Sharma", "email": "arjun@student.ai"})
    call("POST", f"/sessions/{session['id']}/consent")
    call("POST", f"/sessions/{session['id']}/liveness")
    questions = call("GET", f"/sessions/{session['id']}/questions")
    call("POST", f"/sessions/{session['id']}/answers", {
        "question_id": questions[0]["id"],
        "answer_text": "This answer is based only on the uploaded material.",
        "time_spent_seconds": 90,
    })
    report = call("POST", f"/sessions/{session['id']}/reports/generate")
    print(json.dumps({
        "status": "ok",
        "exam": exam["id"],
        "material_chunks": material["chunk_count"],
        "generated_questions": generated["count"],
        "session": session["id"],
        "report": report["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
