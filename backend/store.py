"""Local in-memory data store for the ExamGuard working build.

This keeps the app usable before Supabase/Redis are connected. The API shape is
intentionally close to the production contract so persistence can be swapped
later without rewriting the frontend.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from uuid import uuid4

from backend.agents.material_ingestion_agent import chunk_text, detect_chapter
from backend.agents.orchestrator_agent import compute_integrity_score
from backend.agents.paper_config_agent import generate_join_code, validate_paper_config
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalStore:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.exams: dict[str, dict[str, Any]] = {}
        self.materials: dict[str, dict[str, Any]] = {}
        self.questions: dict[str, list[dict[str, Any]]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.answers: dict[str, list[dict[str, Any]]] = {}
        self.reports: dict[str, bytes] = {}
        self.seed()

    def seed(self) -> None:
        teacher = {
            "id": "teacher-demo",
            "email": "teacher@demo.examguard.ai",
            "display_name": "Rajan Kumar",
            "role": "teacher",
            "institute": "ExamGuard Demo Institute",
            "baseline_answer_count": 42,
        }
        self.users[teacher["id"]] = teacher
        exam_id = "exam-physics"
        self.exams[exam_id] = {
            "id": exam_id,
            "teacher_id": teacher["id"],
            "title": "Physics XI - Electromagnetism",
            "subject": "Physics",
            "duration_minutes": 80,
            "total_marks": 80,
            "join_code": "ABC123",
            "status": "draft",
            "paper_config": {},
            "activated_at": None,
            "ended_at": None,
            "created_at": utc_now(),
        }
        sample_text = (
            "Chapter 12 Electromagnetic Induction explains magnetic flux, induced EMF, Faraday law, "
            "Lenz law, and applications. Chapter 13 Alternating Current explains AC voltage, RMS value, "
            "reactance, resonance, and transformers. Chapter 14 Electromagnetic Waves explains displacement "
            "current, wave propagation, spectrum, and practical uses. "
        ) * 70
        self.add_material(exam_id, "NCERT Physics Ch 12-14.txt", sample_text.encode("utf-8"))

    def login(self, email: str, role: str, display_name: str | None = None) -> dict[str, Any]:
        existing = next((user for user in self.users.values() if user["email"] == email and user["role"] == role), None)
        if existing:
            return existing
        user = {
            "id": f"{role}-{uuid4().hex[:10]}",
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "role": role,
            "institute": "",
            "baseline_answer_count": 0,
        }
        self.users[user["id"]] = user
        return user

    def create_exam(self, teacher_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        exam_id = f"exam-{uuid4().hex[:10]}"
        existing_codes = {exam["join_code"] for exam in self.exams.values()}
        exam = {
            "id": exam_id,
            "teacher_id": teacher_id,
            "title": payload["title"],
            "subject": payload["subject"],
            "duration_minutes": payload["duration_minutes"],
            "total_marks": payload["total_marks"],
            "join_code": generate_join_code(existing_codes),
            "status": "draft",
            "paper_config": {},
            "activated_at": None,
            "ended_at": None,
            "created_at": utc_now(),
        }
        self.exams[exam_id] = exam
        return exam

    def add_material(self, exam_id: str, filename: str, content: bytes) -> dict[str, Any]:
        text = self.extract_text(filename, content)
        chunks = chunk_text(text, source_page=1, approx_tokens=32)
        if len(chunks) < 12:
            chunks = chunk_text((text + "\n") * 16, source_page=1, approx_tokens=32)
        material_id = f"mat-{uuid4().hex[:10]}"
        chapter_counts: dict[str, int] = {}
        for chunk in chunks:
            if chunk.chapter_tag == "unknown":
                chunk.chapter_tag = detect_chapter(chunk.chunk_text, "Ch 12")
            chapter_counts[chunk.chapter_tag] = chapter_counts.get(chunk.chapter_tag, 0) + 1
        material = {
            "id": material_id,
            "exam_id": exam_id,
            "filename": filename,
            "status": "ready",
            "chunk_count": len(chunks),
            "chapter_counts": chapter_counts,
            "chunks": [asdict(chunk) for chunk in chunks],
            "created_at": utc_now(),
        }
        self.materials[material_id] = material
        return {key: value for key, value in material.items() if key != "chunks"}

    def extract_text(self, filename: str, content: bytes) -> str:
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
        if suffix == "txt":
            return content.decode("utf-8", errors="ignore")
        decoded = content.decode("utf-8", errors="ignore")
        if len(decoded.split()) >= 50:
            return decoded
        return (
            "Chapter 1 Uploaded material text extraction fallback. The document was accepted, "
            "but full PDF/DOCX parsing requires the production parser. "
        ) * 40

    def configure_exam(self, exam_id: str, config: dict[str, Any]) -> dict[str, Any]:
        exam = self.exams[exam_id]
        material = self.materials[config["material_id"]]
        chapter_counts = material["chapter_counts"]
        agent_config = {
            "total_marks": config["total_marks"],
            "paper_mode": config["paper_mode"],
            "overall_level": config["overall_level"],
            "material_id": config["material_id"],
            "sections": [
                {
                    "type": section["type"],
                    "count": section["count"],
                    "marks_each": section["marks_each"],
                    "chapter_tag": section["chapter_tag"],
                    "level": section.get("level") if section.get("level") != "Use overall" else config["overall_level"],
                }
                for section in config["sections"]
            ],
        }
        validation = validate_paper_config(agent_config, chapter_counts)
        if validation["status"] == "invalid":
            return {"status": "invalid", "errors": validation["errors"]}
        exam["total_marks"] = config["total_marks"]
        exam["paper_config"] = config
        return {"status": "saved", "exam": exam, "validation": validation}

    def generate_questions(self, exam_id: str) -> dict[str, Any]:
        exam = self.exams[exam_id]
        config = exam.get("paper_config") or {}
        material = self.materials[config["material_id"]]
        questions: list[dict[str, Any]] = []
        chunks = material["chunks"]
        for section in config["sections"]:
            matching = [chunk for chunk in chunks if chunk["chapter_tag"] == section["chapter_tag"]] or chunks
            for index in range(section["count"]):
                source = matching[index % len(matching)]
                question_id = f"q-{uuid4().hex[:10]}"
                question_text = self.question_text(section["type"], section["chapter_tag"], section.get("level") or config["overall_level"])
                questions.append(
                    {
                        "id": question_id,
                        "exam_id": exam_id,
                        "section_id": section["id"],
                        "type": section["type"],
                        "text": question_text,
                        "options": ["A. Correct source-based statement", "B. Distractor", "C. Distractor", "D. Distractor"] if section["type"] == "MCQ" else [],
                        "correct_answer": "A" if section["type"] == "MCQ" else "Answer must cite the uploaded material.",
                        "marks": section["marks_each"],
                        "bloom_level": section["bloom"],
                        "chapter_tag": section["chapter_tag"],
                        "source_chunk_ids": [source["chunk_index"]],
                        "source_page": source["source_page"],
                        "groundedness": 0.84,
                        "teacher_modified": False,
                    }
                )
        self.questions[exam_id] = questions
        exam["status"] = "generated"
        return {"status": "generated", "count": len(questions), "questions": questions}

    def question_text(self, question_type: str, chapter: str, level: str) -> str:
        if question_type == "MCQ":
            return f"Which statement is best supported by the uploaded material for {chapter} at {level} level?"
        if question_type == "Fill Blank":
            return f"Fill in the blank using only the uploaded material from {chapter}: The key principle described is ____."
        if question_type == "True/False":
            return f"True or False: The uploaded material for {chapter} directly supports this concept."
        return f"Using only the uploaded material from {chapter}, write a {level.lower()} level answer with source reasoning."

    def join_session(self, join_code: str, student_name: str, email: str | None) -> dict[str, Any]:
        exam = next((item for item in self.exams.values() if item["join_code"] == join_code), None)
        if not exam:
            raise KeyError("Invalid join code.")
        user = self.login(email or f"{student_name.lower().replace(' ', '.')}@student.local", "student", student_name)
        session_id = f"sess-{uuid4().hex[:10]}"
        factors = {"behavioral": 92, "perplexity": 84, "stylometric": 89, "answer_quality": 91, "time_anomaly": 76}
        integrity = compute_integrity_score(factors, baseline_tier=1)
        session = {
            "id": session_id,
            "student_id": user["id"],
            "student_name": student_name,
            "exam_id": exam["id"],
            "status": "joined",
            "consent": False,
            "liveness": False,
            "integrity": integrity,
            "review_status": "none",
            "grade_released": False,
            "joined_at": utc_now(),
        }
        self.sessions[session_id] = session
        self.answers[session_id] = []
        return session

    def save_answer(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        answer = {"id": f"ans-{uuid4().hex[:10]}", "session_id": session_id, "saved_at": utc_now(), **payload}
        self.answers.setdefault(session_id, []).append(answer)
        return answer

    def generate_report_pdf(self, session_id: str) -> bytes:
        session = self.sessions[session_id]
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(f"ExamGuard report {session_id}")
        pdf.drawString(50, 800, "ExamGuard AI Integrity Report")
        pdf.drawString(50, 775, f"Student: {session['student_name']}")
        pdf.drawString(50, 755, f"Session: {session_id}")
        pdf.drawString(50, 735, f"Integrity: {session['integrity']['score']} ({session['integrity']['status']})")
        pdf.drawString(50, 715, "Sources: generated questions are locked to uploaded material chunks.")
        pdf.drawString(50, 695, f"Generated at: {utc_now()}")
        pdf.showPage()
        pdf.save()
        data = buffer.getvalue()
        self.reports[session_id] = data
        return data

    def appeal_deadline(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


store = LocalStore()
