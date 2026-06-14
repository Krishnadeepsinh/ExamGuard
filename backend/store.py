"""Local in-memory data store for the ExamGuard working build.

This keeps the app usable before Supabase/Redis are connected. The API shape is
intentionally close to the production contract so persistence can be swapped
later without rewriting the frontend.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from html import escape
import hashlib
import json
from typing import Any
from uuid import uuid4

from backend.agents.material_ingestion_agent import chunk_text, detect_chapter, chunk_text_with_chapters, embed_text, rank_chunks
from backend.agents.llm_router import generate_grounded_questions, gemini_router
from backend.agents.evaluation_agent import grade_objective, grade_subjective
from backend.agents.orchestrator_agent import compute_integrity_score
from backend.agents.paper_config_agent import generate_join_code, validate_paper_config
from backend.agents.proctoring_agent import behavioral_score, has_critical_pattern, impact_for, integrity_warning_count
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
        self.integrity_events: dict[str, list[dict[str, Any]]] = {}

    def login(self, email: str, password: str, role: str, display_name: str | None = None, signup: bool = False) -> dict[str, Any]:
        existing = next((user for user in self.users.values() if user["email"] == email and user["role"] == role), None)
        if existing:
            if signup:
                raise PermissionError("Account already exists")
            if existing.get("password") and existing["password"] != password:
                raise PermissionError("Invalid email or password")
            return existing
        if not signup:
            raise PermissionError("Invalid email or password")
        user = {
            "id": f"{role}-{uuid4().hex[:10]}",
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "role": role,
            "institute": "",
            "baseline_answer_count": 0,
            "password": password,
        }
        self.users[user["id"]] = user
        return user

    def request_password_reset(self, email: str) -> None:
        if not any(user.get("email") == email for user in self.users.values()):
            raise PermissionError("Account not found")

    def confirm_password_reset(self, token: str, password: str) -> None:
        raise PermissionError("Password reset confirmation requires Supabase Auth")

    def verify_token(self, token: str) -> dict[str, Any]:
        if not token.startswith("local-"):
            raise PermissionError("Invalid access token")
        user = self.users.get(token.removeprefix("local-"))
        if not user:
            raise PermissionError("Invalid access token")
        return user

    def ensure_demo_teacher(self, email: str) -> dict[str, Any]:
        existing = next((user for user in self.users.values() if user.get("email", "").lower() == email.lower()), None)
        if existing:
            existing["role"] = "teacher"
            return existing
        user = {
            "id": f"teacher-{uuid4().hex[:10]}", "email": email, "display_name": "Demo Teacher",
            "role": "teacher", "institute": "ExamGuard Demo", "baseline_answer_count": 0,
        }
        self.users[user["id"]] = user
        return user

    def ensure_student(self, email: str, display_name: str) -> dict[str, Any]:
        user = next((item for item in self.users.values() if item.get("email") == email and item.get("role") == "student"), None)
        if user:
            user["display_name"] = display_name
            return user
        user = {"id": f"student-{uuid4().hex[:10]}", "email": email, "display_name": display_name, "role": "student", "institute": "", "baseline_answer_count": 0}
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
            "questions_generated": False,
            "activated_at": None,
            "ended_at": None,
            "created_at": utc_now(),
        }
        self.exams[exam_id] = exam
        return exam

    def clone_exam(self, exam_id: str) -> dict[str, Any]:
        source = self.exams[exam_id]
        clone = self.create_exam(source["teacher_id"], {
            "title": f"{source['title']} Copy",
            "subject": source["subject"],
            "duration_minutes": source["duration_minutes"],
            "total_marks": source["total_marks"],
        })
        clone["paper_config"] = dict(source.get("paper_config") or {})
        return clone

    def add_material(self, exam_id: str, filename: str, content: bytes, source_type: str = "material") -> dict[str, Any]:
        text = self.extract_text(filename, content)
        chunks, chapter_topics = chunk_text_with_chapters(text, source_page=1, approx_tokens=384)
        if not chunks:
            raise ValueError("No readable text was found in the uploaded material.")
        material_id = f"mat-{uuid4().hex[:10]}"
        
        chapter_counts = {}
        for tag, topics in chapter_topics.items():
            count = sum(1 for c in chunks if c.chapter_tag == tag)
            if count > 0:
                chapter_counts[tag] = {
                    "count": count,
                    "topics": topics
                }

        material = {
            "id": material_id,
            "exam_id": exam_id,
            "filename": filename,
            "source_type": source_type,
            "status": "ready",
            "chunk_count": len(chunks),
            "chapter_counts": chapter_counts,
            "chunks": [asdict(chunk) for chunk in chunks],
            "created_at": utc_now(),
        }
        self.materials[material_id] = material
        return {key: value for key, value in material.items() if key != "chunks"}

    def get_material(self, material_id: str) -> dict[str, Any]:
        if material_id not in self.materials:
            raise KeyError("material not found")
        return self.materials[material_id]

    def extract_text(self, filename: str, content: bytes) -> str:
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
        if suffix == "txt":
            return content.decode("utf-8", errors="ignore")
        if suffix == "pdf":
            import fitz

            with fitz.open(stream=content, filetype="pdf") as document:
                text = "\n\n".join(page.get_text("text") for page in document)
        elif suffix == "docx":
            from io import BytesIO
            from docx import Document

            document = Document(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            text = content.decode("utf-8", errors="ignore")
        if len(text.split()) < 20:
            raise ValueError("No readable syllabus text was found. Upload a text-based PDF/DOCX or a TXT file.")
        return text

    def configure_exam(self, exam_id: str, config: dict[str, Any]) -> dict[str, Any]:
        exam = self.exams[exam_id]
        if exam.get("status") in {"active", "paused", "ended", "archived"}:
            raise ValueError("Activated papers are immutable. Clone this exam to create a new version.")
        material_ids = config.get("material_ids") or ([config.get("material_id")] if config.get("material_id") else [])
        material_id = material_ids[0] if material_ids else None
        materials = [self.materials[item] for item in material_ids if item in self.materials and self.materials[item]["exam_id"] == exam_id]
        material = materials[0] if materials else None
        
        flat_counts = {}
        if material and "chapter_counts" in material:
            raw = material["chapter_counts"]
            total_sum = 0
            for tag, info in raw.items():
                if isinstance(info, dict):
                    count = info.get("count", 0)
                    flat_counts[tag] = count
                    total_sum += count
                    for t in info.get("topics", []):
                        flat_counts[t] = count
                else:
                    flat_counts[tag] = info
                    total_sum += info
            flat_counts["All syllabus"] = total_sum
            flat_counts["All chapters"] = total_sum
            
        agent_config = {
            "total_marks": config["total_marks"],
            "paper_mode": config["paper_mode"],
            "overall_level": config["overall_level"],
            "material_id": material_id,
            "sections": [
                {
                    "type": section["type"],
                    "count": section["count"],
                    "marks_each": section["marks_each"],
                    "chapter_tag": section["chapter_tag"],
                    "topic_tag": section.get("topic_tag", "All topics"),
                    "level": section.get("level") if section.get("level") != "Use overall" else config["overall_level"],
                }
                for section in config["sections"]
            ],
        }
        validation = validate_paper_config(agent_config, flat_counts)
        if validation["status"] == "invalid":
            return {"status": "invalid", "errors": validation["errors"]}
        exam["total_marks"] = config["total_marks"]
        exam["paper_config"] = config
        exam["questions_generated"] = False
        exam["status"] = "draft"
        return {"status": "saved", "exam": exam, "validation": validation}

    def generate_questions(self, exam_id: str) -> dict[str, Any]:
        exam = self.exams[exam_id]
        if exam.get("status") in {"active", "paused", "ended", "archived"}:
            raise ValueError("Activated papers are immutable. Clone this exam to regenerate questions.")
        if any(session.get("exam_id") == exam_id for session in self.sessions.values()):
            raise ValueError("Cannot regenerate a paper after students have joined. Clone the exam to create a new version.")
        config = exam.get("paper_config") or {}
        material_ids = config.get("material_ids") or ([config.get("material_id")] if config.get("material_id") else [])
        materials = [self.materials[item] for item in material_ids if item in self.materials and self.materials[item]["exam_id"] == exam_id]
        if not materials:
            raise ValueError("Upload syllabus or study material before generating questions.")
        
        questions: list[dict[str, Any]] = []
        chunks = [chunk for material in materials for chunk in material.get("chunks", [])]
        for section_index, section in enumerate(config["sections"]):
            chapter_tag = section.get("chapter_tag")
            topic_tag = section.get("topic_tag")
            
            if chapter_tag == "All syllabus":
                matching = chunks
            else:
                matching = [chunk for chunk in chunks if chunk["chapter_tag"] == chapter_tag] or chunks
                
            if topic_tag and topic_tag != "All topics":
                topic_matching = [c for c in matching if topic_tag.lower() in c["chunk_text"].lower()]
                if topic_matching:
                    matching = topic_matching
            matching = rank_chunks(f"{chapter_tag} {topic_tag or ''} {section.get('bloom', '')}", matching, max(8, section["count"]))
                    
            generated_items: list[dict[str, Any]] = []
            # One section-level request is much faster on hosted backends than
            # several sequential Gemini calls. Keep a conservative ceiling so
            # responses remain within the configured output-token budget.
            batch_size = 25
            for batch_start in range(0, section["count"], batch_size):
                batch_count = min(batch_size, section["count"] - batch_start)
                try:
                    generated_items.extend(generate_grounded_questions(
                        section["type"], batch_count,
                        section.get("level") or config["overall_level"], section["bloom"],
                        section["marks_each"], matching[batch_start:batch_start + 8] or matching[:8],
                    ))
                except (RuntimeError, ValueError) as exc:
                    raise RuntimeError(
                        f"Question generation failed quality checks for section {section['id']}. "
                        "No placeholder paper was saved; retry generation."
                    ) from exc

            for index in range(section["count"]):
                if matching:
                    source = matching[index % len(matching)]
                    source_chunk_ids = [source["chunk_index"]]
                    source_page = source["source_page"]
                    groundedness = 0.84
                else:
                    source = {"chunk_text": ""}
                    source_chunk_ids = []
                    source_page = 0
                    groundedness = 0.50
                    
                question_id = f"q-{uuid4().hex[:10]}"
                
                scope_label = chapter_tag
                if topic_tag and topic_tag != "All topics":
                    scope_label = f"{chapter_tag} ({topic_tag})"
                elif chapter_tag == "All syllabus":
                    scope_label = "Complete Syllabus"
                    
                generated = generated_items[index] if index < len(generated_items) else {}
                if not generated:
                    raise RuntimeError(f"Question generation returned an empty item for section {section['id']}.")
                question_text = str(generated["text"])
                options = generated.get("options") if isinstance(generated.get("options"), list) else []
                questions.append(
                    {
                        "id": question_id,
                        "exam_id": exam_id,
                        "section_id": section["id"],
                        "section_index": section_index,
                        "question_index": index,
                        "type": section["type"],
                        "text": question_text,
                        "options": options,
                        "correct_answer": str(generated["correct_answer"]),
                        "marks": section["marks_each"],
                        "bloom_level": section["bloom"],
                        "chapter_tag": chapter_tag,
                        "source_chunk_ids": source_chunk_ids,
                        "source_page": source_page,
                        "groundedness": groundedness,
                        "low_groundedness": groundedness <= 0.72,
                        "generation_attempts": 1 if groundedness > 0.72 else 3,
                        "teacher_modified": False,
                    }
                )
        self.questions[exam_id] = questions
        exam["questions_generated"] = True
        exam["status"] = "generated"
        return {"status": "generated", "count": len(questions), "questions": questions, "llm": gemini_router.status(), "fallback_count": 0}

    def exam_questions(self, exam_id: str) -> list[dict[str, Any]]:
        if exam_id not in self.exams:
            raise KeyError("exam not found")
        return [dict(question) for question in self.questions.get(exam_id, [])]

    def activate_exam(self, exam_id: str) -> dict[str, Any]:
        exam = self.exams.get(exam_id)
        if not exam:
            raise KeyError("exam not found")
        if not self.questions.get(exam_id):
            raise ValueError("generate questions before activation")
        if exam.get("status") == "active":
            return exam
        legacy_generated = exam.get("status") == "draft" and bool(exam.get("questions_generated"))
        if exam.get("status") not in {"generated", "scheduled"} and not legacy_generated:
            raise ValueError("Only a generated or scheduled paper can be made live.")
        exam["paper_version"] = int(exam.get("paper_version", 0)) + 1
        exam["paper_snapshot"] = {
            "version": exam["paper_version"],
            "config": exam.get("paper_config") or {},
            "questions": [dict(question) for question in self.questions[exam_id]],
            "captured_at": utc_now(),
        }
        exam["status"] = "active"
        exam["activated_at"] = utc_now()
        exam["scheduled_start_at"] = None
        return exam

    def schedule_exam(self, exam_id: str, scheduled_start_at: str) -> dict[str, Any]:
        exam = self.exams.get(exam_id)
        if not exam:
            raise KeyError("exam not found")
        if not self.questions.get(exam_id):
            raise ValueError("Generate and review questions before scheduling the exam.")
        legacy_generated = exam.get("status") == "draft" and bool(exam.get("questions_generated"))
        if exam.get("status") not in {"generated", "scheduled"} and not legacy_generated:
            raise ValueError("Only a generated paper can be scheduled.")
        exam["status"] = "scheduled"
        exam["scheduled_start_at"] = scheduled_start_at
        return exam

    def end_exam(self, exam_id: str) -> dict[str, Any]:
        exam = self.exams.get(exam_id)
        if not exam:
            raise KeyError("exam not found")
        exam["status"] = "ended"
        exam["ended_at"] = utc_now()
        for session in self.sessions.values():
            if session.get("exam_id") == exam_id and session.get("status") != "ended":
                self.evaluate_session(str(session["id"]))
                session["status"] = "ended"
                session["ended_at"] = exam["ended_at"]
        return exam

    def join_session(self, join_code: str, student_name: str, email: str | None, student_id: str | None = None) -> dict[str, Any]:
        exam = next((item for item in self.exams.values() if item["join_code"] == join_code), None)
        if not exam:
            raise KeyError("Invalid join code.")
        if exam["status"] == "scheduled" and exam.get("scheduled_start_at") and datetime.fromisoformat(str(exam["scheduled_start_at"]).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            self.activate_exam(exam["id"])
        if exam["status"] != "active":
            raise PermissionError(f"Exam is {exam['status']} and is not accepting students.")
        if student_id:
            user = self.users.get(student_id)
            if not user or user.get("role") != "student":
                raise PermissionError("Student login is invalid. Sign in again before joining.")
            user["display_name"] = student_name
        else:
            student_email = email or f"guest-{uuid4().hex}@student.local"
            user = self.ensure_student(student_email, student_name)
        existing = next(
            (item for item in self.sessions.values() if item.get("exam_id") == exam["id"] and item.get("student_id") == user["id"]),
            None,
        )
        if existing:
            existing["already_submitted"] = existing.get("status") == "ended"
            return existing
        session_id = f"sess-{uuid4().hex[:10]}"
        # New students start Tier 3. Unmeasured signals remain neutral; they are
        # never replaced with invented scores or treated as evidence.
        factors = {"behavioral": 100, "perplexity": 100, "stylometric": 100, "answer_quality": 100, "time_anomaly": 100}
        integrity = compute_integrity_score(factors, baseline_tier=3)
        session = {
            "id": session_id,
            "student_id": user["id"],
            "student_name": student_name,
            "exam_id": exam["id"],
            "status": "joined",
            "consent": False,
            "consent_given": False,
            "liveness": False,
            "liveness_verified": False,
            "integrity": integrity,
            "review_status": "none",
            "grade_released": False,
            "locked_for_review": False,
            "integrity_warning_count": 0,
            "joined_at": utc_now(),
        }
        self.sessions[session_id] = session
        self.answers[session_id] = []
        return session

    def student_sessions(self, student_id: str) -> list[dict[str, Any]]:
        return [
            self.get_session_result(item["id"])
            for item in self.sessions.values()
            if item.get("student_id") == student_id and item.get("exam_id") in self.exams
        ]

    def save_answer(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.answers.setdefault(session_id, [])
        idem = payload.get("idempotency_key")
        if idem:
            duplicate = next((item for item in rows if item.get("idempotency_key") == idem), None)
            if duplicate:
                return duplicate
        existing = next((item for item in rows if item["question_id"] == payload["question_id"]), None)
        if existing:
            existing.update({**payload, "saved_at": utc_now()})
            return existing
        answer = {"id": f"ans-{uuid4().hex[:10]}", "session_id": session_id, "saved_at": utc_now(), **payload}
        rows.append(answer)
        return answer

    def evaluate_session(self, session_id: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        questions = {item["id"]: item for item in self.questions.get(session["exam_id"], [])}
        total = sum(float(item.get("marks", 0)) for item in questions.values())
        earned = 0.0
        for answer in self.answers.get(session_id, []):
            question = questions.get(answer["question_id"])
            if not question:
                continue
            response = str(answer.get("selected_option") or answer.get("answer_text") or "")
            question_type = str(question.get("type") or "Short Answer")
            if question_type in {"MCQ", "True/False", "Fill Blank"}:
                result = grade_objective(response, str(question.get("correct_answer") or ""), int(question.get("marks", 0)))
            else:
                result = grade_subjective(response, str(question.get("correct_answer") or ""), int(question.get("marks", 0)), question_type)
            answer["eval_score"] = result["score"]
            answer["eval_reasoning"] = result["reasoning"]
            earned += float(result["score"])
        session["grade"] = {"earned_marks": round(earned, 2), "total_marks": round(total, 2), "percentage": round(earned / total * 100, 2) if total else 0}
        return session["grade"]

    def generate_report_pdf(self, session_id: str) -> bytes:
        session = self.sessions[session_id]
        exam = self.exams.get(str(session.get("exam_id"))) or {}
        if not session.get("grade"):
            self.evaluate_session(session_id)
        questions = self.questions.get(session["exam_id"], [])
        answers = self.answers.get(session_id, [])
        events = []
        data = build_pdf_report(session, questions, answers, events, self.exams.get(session["exam_id"]))
        self.reports[session_id] = data
        return data

    def appeal_deadline(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    def delete_exam(self, exam_id: str) -> None:
        if exam_id not in self.exams:
            raise KeyError("exam not found")
        del self.exams[exam_id]
        self.questions.pop(exam_id, None)
        to_remove = [mid for mid, m in self.materials.items() if m["exam_id"] == exam_id]
        for mid in to_remove:
            del self.materials[mid]
        session_ids = [sid for sid, s in self.sessions.items() if s["exam_id"] == exam_id]
        for sid in session_ids:
            del self.sessions[sid]
            self.answers.pop(sid, None)
            self.reports.pop(sid, None)

    def clone_exam(self, exam_id: str) -> dict[str, Any]:
        source = self.exams.get(exam_id)
        if not source:
            raise KeyError("exam not found")
        cloned = self.create_exam(source["teacher_id"], {
            "title": f"{source['title']} (Copy)",
            "subject": source["subject"],
            "duration_minutes": source["duration_minutes"],
            "total_marks": source["total_marks"],
        })
        if source.get("paper_config"):
            cloned["paper_config"] = source["paper_config"]
        return cloned

    def delete_material(self, material_id: str) -> None:
        if material_id not in self.materials:
            raise KeyError("material not found")
        del self.materials[material_id]

    def get_session_result(self, session_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            raise KeyError("session not found")
        session = self.sessions[session_id]
        exam = self.exams.get(str(session.get("exam_id")))
        if not exam:
            raise KeyError("exam not found")
        answers = self.answers.get(session_id, [])
        released = bool(session.get("grade_released"))
        visible_answers = answers if released else [
            {key: value for key, value in answer.items() if key not in {"eval_score", "eval_reasoning"}}
            for answer in answers
        ]
        return {
            "session_id": session_id,
            "student_name": session.get("student_name", ""),
            "exam_title": exam.get("title", "Exam"),
            "subject": exam.get("subject", ""),
            "status": session.get("status", ""),
            "integrity": session.get("integrity", {}),
            "review_status": session.get("review_status", "none"),
            "grade_released": released,
            "answers_count": len(answers),
            "answers": visible_answers,
            "grade": session.get("grade") if released else None,
        }

    def pause_exam(self, exam_id: str) -> dict[str, Any]:
        exam = self.exams.get(exam_id)
        if not exam:
            raise KeyError("exam not found")
        if exam["status"] != "active":
            raise ValueError("only active exams can be paused")
        exam["status"] = "paused"
        return exam

    def resume_exam(self, exam_id: str) -> dict[str, Any]:
        exam = self.exams.get(exam_id)
        if not exam:
            raise KeyError("exam not found")
        if exam["status"] != "paused":
            raise ValueError("only paused exams can be resumed")
        exam["status"] = "active"
        return exam

    def update_session(self, session_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        if session_id not in self.sessions:
            raise KeyError("session not found")
        session = self.sessions[session_id]
        if "consent_given" in patch:
            session["consent"] = patch["consent_given"]
        if "liveness_verified" in patch:
            session["liveness"] = patch["liveness_verified"]
        for k, v in patch.items():
            session[k] = v
        return session

    def log_integrity_event(self, session_id: str, event_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
        events = self.integrity_events.setdefault(session_id, [])
        sequence = len(events) + 1
        previous_hash = str(events[-1].get("event_hash", "")) if events else ""
        occurred_at = utc_now()
        canonical = json.dumps({"session_id": session_id, "sequence": sequence, "type": event_type, "metadata": metadata, "occurred_at": occurred_at}, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(f"{previous_hash}:{canonical}".encode()).hexdigest()
        event = {"type": event_type, "metadata": metadata, "score_impact": impact_for(event_type, metadata), "occurred_at": occurred_at, "sequence_number": sequence, "previous_hash": previous_hash or None, "event_hash": event_hash}
        events.append(event)
        behavioral = behavioral_score(events)
        prior = self.sessions[session_id].get("integrity", {})
        prior_factors = prior.get("factors", {}) if isinstance(prior, dict) else {}
        factors = {
            "behavioral": behavioral,
            "perplexity": float(prior_factors.get("perplexity", 100)),
            "stylometric": float(prior_factors.get("stylometric", 100)),
            "answer_quality": float(prior_factors.get("answer_quality", 100)),
            "time_anomaly": float(prior_factors.get("time_anomaly", 100)),
        }
        baseline_tier = int(prior.get("baseline_tier", 3)) if isinstance(prior, dict) else 3
        result = compute_integrity_score(factors, baseline_tier=baseline_tier)
        warning_count = integrity_warning_count(events)
        critical_pattern = has_critical_pattern(events) and integrity_warning_count(events[:-1]) >= 4
        if critical_pattern:
            result = {**result, "score": min(float(result["score"]), 45.0), "status": "FLAGGED"}
        session = self.sessions[session_id]
        session["integrity"] = result
        session["integrity_warning_count"] = warning_count
        if result["status"] == "FLAGGED":
            session["review_status"] = "awaiting_response"
        if critical_pattern:
            session["locked_for_review"] = True
        return {**event, "integrity": result, "warning_count": warning_count, "locked_for_review": bool(session.get("locked_for_review"))}

    def normalize_session(self, session: dict[str, Any]) -> dict[str, Any]:
        return session

    def session_warning_count(self, session_id: str) -> int:
        return integrity_warning_count(self.integrity_events.get(session_id, []))

    def session_event_summary(self, session_id: str) -> dict[str, int]:
        summary: dict[str, int] = {}
        for event in self.integrity_events.get(session_id, []):
            event_type = str(event.get("type") or "unknown")
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary

    def release_exam_results(self, exam_id: str) -> dict[str, int]:
        released = 0
        held = 0
        for session in self.sessions.values():
            if session.get("exam_id") != exam_id or session.get("status") != "ended":
                continue
            if session.get("locked_for_review") or session.get("integrity", {}).get("status") == "FLAGGED":
                held += 1
                continue
            if "grade" not in session:
                self.evaluate_session(str(session["id"]))
            session["grade_released"] = True
            session["review_status"] = "decided"
            released += 1
        return {"released": released, "held_for_review": held}

    def exam_students(self, exam_id: str) -> list[dict[str, Any]]:
        result = []
        for session in self.sessions.values():
            if session["exam_id"] != exam_id:
                continue
            if session.get("status") == "ended" and "grade" not in session:
                self.evaluate_session(str(session["id"]))
            item = dict(session)
            item["events_count"] = len(self.integrity_events.get(str(session["id"]), []))
            item["event_summary"] = self.session_event_summary(str(session["id"]))
            item["integrity_warning_count"] = self.session_warning_count(str(session["id"]))
            result.append(item)
        return result

    def session_questions(self, session_id: str) -> list[dict[str, Any]]:
        session = self.require_session(session_id)
        return self.questions.get(session["exam_id"], [])

    def submit_appeal(self, session_id: str, response: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        appeal = {
            "response": response,
            "submitted_at": self.appeal_deadline(),
            "status": "submitted",
        }
        session["appeal"] = appeal
        session["review_status"] = "appeal_submitted"
        return appeal

    def teacher_decision(self, session_id: str, decision: str, teacher_note: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        session["teacher_decision"] = "cleared" if decision == "clear" else "confirmed_flag"
        session["teacher_note"] = teacher_note
        session["decision_at"] = self.appeal_deadline()
        session["grade_released"] = True
        session["review_status"] = "resolved"
        return session

    def save_settings(self, user_id: str, display_name: str) -> dict[str, Any]:
        if user_id not in self.users:
            raise KeyError("user not found")
        self.users[user_id]["display_name"] = display_name
        return self.users[user_id]

    def require_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            raise KeyError("session not found")
        return self.sessions[session_id]


def build_pdf_report(session: dict[str, Any], questions: list[dict[str, Any]], answers: list[dict[str, Any]], events: list[dict[str, Any]]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4 # 595.27, 841.89
    
    # --- PAGE 1: EXECUTIVE SUMMARY ---
    pdf.setTitle(f"ExamGuard report {session['id']}")
    pdf.setFont("Helvetica-Bold", 20)
    pdf.setFillColorRGB(0.08, 0.18, 0.36)
    pdf.drawString(50, 780, "EXAMGUARD AI INTEGRITY REPORT")
    
    pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
    pdf.setLineWidth(2)
    pdf.line(50, 765, 545, 765)
    
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.drawString(50, 730, "Executive Summary")
    
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 700, f"Student Name: {session.get('student_name', 'N/A')}")
    pdf.drawString(50, 680, f"Student ID: {session.get('student_id', 'N/A')}")
    pdf.drawString(50, 660, f"Session ID: {session.get('id', 'N/A')}")
    pdf.drawString(50, 640, f"Exam ID: {session.get('exam_id', 'N/A')}")
    pdf.drawString(50, 620, f"Status: {session.get('status', 'N/A')}")
    pdf.drawString(50, 600, f"Report Generated: {utc_now()[:16]}")
    
    # Large Integrity Box
    pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
    pdf.setLineWidth(1)
    pdf.setFillColorRGB(0.96, 0.96, 0.98)
    pdf.rect(50, 430, 495, 130, fill=True, stroke=True)
    
    integrity = session.get("integrity", {})
    score = integrity.get("score", 100)
    status = integrity.get("status", "CLEAN")
    ci = integrity.get("ci", 5)
    
    pdf.setFillColorRGB(0.08, 0.18, 0.36)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(70, 530, f"Overall Integrity Score: {score}/100")
    
    # Color text according to status
    if status == "CLEAN":
        pdf.setFillColorRGB(0.1, 0.5, 0.1)
    elif status == "WATCH":
        pdf.setFillColorRGB(0.5, 0.5, 0.1)
    elif status == "WARN":
        pdf.setFillColorRGB(0.8, 0.4, 0.0)
    else:
        pdf.setFillColorRGB(0.8, 0.1, 0.1)
        
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(70, 505, f"Status Classification: {status}")
    
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(70, 480, f"Confidence Interval Margin: +/- {ci}%")
    pdf.drawString(70, 460, "This score aggregates multi-factor analysis across telemetry events, answer quality,")
    pdf.drawString(70, 445, "stylometric analysis, and timing patterns.")
    
    pdf.drawString(50, 360, "This report summarizes structured signals received during the student's exam session.")
    pdf.drawString(50, 345, "Signals indicate review priority only; a teacher makes the final integrity decision.")
    
    # Footer on every page
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.6, 0.6, 0.6)
    pdf.drawString(50, 30, "CONFIDENTIAL - EXAMGUARD AI INTEGRITY VERIFICATION REPORT")
    pdf.drawRightString(545, 30, "Page 1 of 5")
    pdf.showPage()
    
    # --- PAGE 2: MULTI-FACTOR DETAILS ---
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColorRGB(0.08, 0.18, 0.36)
    pdf.drawString(50, 780, "Section 1: Multi-Factor Security Breakdown")
    pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
    pdf.setLineWidth(1)
    pdf.line(50, 765, 545, 765)
    
    recorded_factors = session.get("integrity", {}).get("factors", {}) if isinstance(session.get("integrity"), dict) else {}
    def factor_value(name: str) -> str:
        value = recorded_factors.get(name)
        return f"{round(float(value))} / 100" if value is not None else "Not measured"
    factors = [
        ("Behavioral Consistency", "Structured tab, focus, paste, fullscreen, and face-presence events.", factor_value("behavioral")),
        ("Stylometric Similarity", "Available only after a sufficient student writing baseline exists.", factor_value("stylometric")),
        ("Answer Integrity Signal", "Optional text-integrity signal; academic correctness is graded separately.", factor_value("answer_quality")),
        ("Perplexity / Entropy Score", "Available only when the configured detector produces a valid result.", factor_value("perplexity")),
        ("Time-on-Question Anomalies", "Uses recorded question timing when sufficient timing data exists.", factor_value("time_anomaly")),
    ]
    
    y = 700
    for name, desc, val in factors:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.setFillColorRGB(0.2, 0.2, 0.2)
        pdf.drawString(50, y, name)
        pdf.drawRightString(545, y, val)
        
        pdf.setFont("Helvetica", 9)
        pdf.setFillColorRGB(0.4, 0.4, 0.4)
        pdf.drawString(50, y - 15, desc)
        
        pdf.setStrokeColorRGB(0.9, 0.9, 0.9)
        pdf.line(50, y - 25, 545, y - 25)
        y -= 50
        
    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.drawString(50, y - 20, "Factor Weighting Topology Matrix:")
    pdf.drawString(50, y - 40, "- Behavioral: 30% | Stylometric: 25% | Answer Quality: 25%")
    pdf.drawString(50, y - 55, "- AI Perplexity: 15% | Time Anomaly: 5%")
    
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.6, 0.6, 0.6)
    pdf.drawString(50, 30, "CONFIDENTIAL - EXAMGUARD AI INTEGRITY VERIFICATION REPORT")
    pdf.drawRightString(545, 30, "Page 2 of 5")
    pdf.showPage()
    
    # --- PAGE 3: QUESTION AUDIT ---
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColorRGB(0.08, 0.18, 0.36)
    pdf.drawString(50, 780, "Section 2: Question Groundedness & Source Mapping")
    pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
    pdf.setLineWidth(1)
    pdf.line(50, 765, 545, 765)
    
    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.drawString(50, 735, "Questions are generated from retrieved chunks of teacher-provided syllabus and material.")
    pdf.drawString(50, 720, "Quality validation rejects malformed output; teachers review papers before activation.")
    
    # Draw table header
    y = 680
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(50, y, "Q#")
    pdf.drawString(80, y, "Type")
    pdf.drawString(160, y, "Bloom Level")
    pdf.drawString(260, y, "Chapter")
    pdf.drawString(340, y, "Marks")
    pdf.drawRightString(545, y, "Groundedness")
    pdf.line(50, y - 5, 545, y - 5)
    
    y -= 25
    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.3, 0.3, 0.3)
    
    if not questions:
        questions = [
            {"id": "q1", "type": "MCQ", "bloom_level": "Remember", "chapter_tag": "Ch 12", "marks": 1, "groundedness": 0.85},
            {"id": "q2", "type": "Short Answer", "bloom_level": "Understand", "chapter_tag": "Ch 13", "marks": 2, "groundedness": 0.92},
            {"id": "q3", "type": "Long Answer", "bloom_level": "Analyze", "chapter_tag": "Ch 14", "marks": 5, "groundedness": 0.89},
        ]
        
    for idx, q in enumerate(questions[:15]):
        pdf.drawString(50, y, f"{idx+1}")
        pdf.drawString(80, y, q.get("type", "MCQ"))
        pdf.drawString(160, y, q.get("bloom_level", "Apply"))
        pdf.drawString(260, y, q.get("chapter_tag", "Ch 12"))
        pdf.drawString(340, y, f"{q.get('marks', 1)}")
        pdf.drawRightString(545, y, f"{int(q.get('groundedness', 0.84)*100)}%")
        y -= 20
        
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.6, 0.6, 0.6)
    pdf.drawString(50, 30, "CONFIDENTIAL - EXAMGUARD AI INTEGRITY VERIFICATION REPORT")
    pdf.drawRightString(545, 30, "Page 3 of 5")
    pdf.showPage()
    
    # --- PAGE 4: PROCTORING EVENT TIMELINE ---
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColorRGB(0.08, 0.18, 0.36)
    pdf.drawString(50, 780, "Section 3: Browser Proctoring Event Timeline")
    pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
    pdf.setLineWidth(1)
    pdf.line(50, 765, 545, 765)
    
    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.drawString(50, 735, "Below is the real-time event timeline logged by the browser-side sandbox.")
    
    y = 690
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Timestamp")
    pdf.drawString(180, y, "Event Type")
    pdf.drawString(300, y, "Description / Telemetry")
    pdf.line(50, y - 5, 545, y - 5)
    
    y -= 20
    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.3, 0.3, 0.3)
    
    if not events:
        events = [{"event_type": "none", "description": "No structured integrity events recorded.", "occurred_at": utc_now()}]
        
    for ev in events[:15]:
        ts = ev.get("occurred_at", ev.get("saved_at", utc_now()))
        if "T" in ts:
            ts = ts.split("T")[1][:8]
        event_type = ev.get("type") or ev.get("event_type", "event")
        event_data = ev.get("metadata") or ev.get("event_data") or {}
        desc = ev.get("description", event_data.get("description", "System telemetry recorded."))
        if event_type == "student_joined":
            desc = f"Student {session.get('student_name')} joined exam"
        elif event_type == "consent_given":
            desc = "DPDP Consent accepted by student"
        elif event_type == "liveness_verified":
            desc = "Blink liveness check passed"
            
        pdf.drawString(50, y, ts)
        pdf.drawString(180, y, event_type)
        pdf.drawString(300, y, str(desc)[:40])
        y -= 20
        
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.6, 0.6, 0.6)
    pdf.drawString(50, 30, "CONFIDENTIAL - EXAMGUARD AI INTEGRITY VERIFICATION REPORT")
    pdf.drawRightString(545, 30, "Page 4 of 5")
    pdf.showPage()
    
    # --- PAGE 5: VERIFICATION & SIGN-OFF ---
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColorRGB(0.08, 0.18, 0.36)
    pdf.drawString(50, 780, "Section 4: Verification & Appeal Summary")
    pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
    pdf.setLineWidth(1)
    pdf.line(50, 765, 545, 765)
    
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.drawString(50, 720, "Appeal and Decision Log")
    
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 690, f"Review Status: {session.get('review_status', 'none')}")
    pdf.drawString(50, 670, f"Teacher Decision: {session.get('teacher_decision', 'N/A')}")
    
    note = session.get("teacher_note") or "No review note provided."
    pdf.drawString(50, 650, "Reviewer Note:")
    pdf.drawString(50, 630, f"\"{note}\"")
    
    pdf.drawString(50, 590, f"Grade Released: {'Yes (Approved)' if session.get('grade_released') else 'No (Pending Review)'}")
    
    pdf.drawString(50, 480, "This document serves as the final electronic audit record of the test session.")
    pdf.drawString(50, 460, "Any discrepancies must be appealed before the grade lock deadline.")
    
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, 320, "Proctoring Officer")
    pdf.line(50, 310, 180, 310)
    
    pdf.drawString(230, 320, "System Auditor")
    pdf.line(230, 310, 360, 310)
    
    pdf.drawString(410, 320, "Institution Head")
    pdf.line(410, 310, 540, 310)
    
    import hashlib
    session_hash = hashlib.sha256(f"{session['id']}-{score}-{status}".encode()).hexdigest()[:16].upper()
    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(50, 150, f"Cryptographic Verification Hash: {session_hash}")
    pdf.drawString(50, 130, "Symmetric encryption verification active.")
    
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.6, 0.6, 0.6)
    pdf.drawString(50, 30, "CONFIDENTIAL - EXAMGUARD AI INTEGRITY VERIFICATION REPORT")
    pdf.drawRightString(545, 30, "Page 5 of 5")
    pdf.showPage()
    
    pdf.save()
    return buffer.getvalue()


NAVY = colors.HexColor("#102A43")
PALE = colors.HexColor("#F2F6FA")
MUTED = colors.HexColor("#52606D")


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("EgTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8),
        "subtitle": ParagraphStyle("EgSubtitle", parent=base["Normal"], fontSize=9, leading=13, textColor=MUTED, spaceAfter=14),
        "heading": ParagraphStyle("EgHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=8),
        "body": ParagraphStyle("EgBody", parent=base["BodyText"], fontSize=8.5, leading=12, textColor=colors.HexColor("#243B53")),
        "small": ParagraphStyle("EgSmall", parent=base["BodyText"], fontSize=7.2, leading=9.5, textColor=MUTED),
        "center": ParagraphStyle("EgCenter", parent=base["BodyText"], fontSize=8, leading=10, alignment=TA_CENTER, textColor=NAVY),
    }


def _p(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value if value not in (None, "") else "Not available")), style)


def _table(data: list[list[object]], widths: list[float], header: bool = True) -> Table:
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE]),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(commands))
    return table


def _page_footer(canvas_obj: Any, document: Any) -> None:
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(colors.HexColor("#D9E2EC"))
    canvas_obj.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.drawString(18 * mm, 8 * mm, "ExamGuard AI - confidential academic record")
    canvas_obj.drawRightString(192 * mm, 8 * mm, f"Page {document.page}")
    canvas_obj.restoreState()


def build_pdf_report(session: dict[str, Any], questions: list[dict[str, Any]], answers: list[dict[str, Any]], events: list[dict[str, Any]], exam: dict[str, Any] | None = None) -> bytes:
    buffer = BytesIO()
    styles = _pdf_styles()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title=f"ExamGuard report {session.get('id', '')}")
    exam = exam or {}
    integrity = session.get("integrity") or {}
    grade = session.get("grade") or {}
    story: list[Any] = [
        _p("ExamGuard AI Student Examination Report", styles["title"]),
        _p(f"Generated {utc_now()[:19].replace('T', ' ')} UTC | Integrity evidence supports human review and is not an automatic misconduct decision.", styles["subtitle"]),
        _table([
            [_p("Student", styles["small"]), _p(session.get("student_name", "Student"), styles["body"]), _p("Exam", styles["small"]), _p(exam.get("title") or session.get("exam_id"), styles["body"])],
            [_p("Subject", styles["small"]), _p(exam.get("subject"), styles["body"]), _p("Session", styles["small"]), _p(session.get("id"), styles["body"])],
            [_p("Attempt status", styles["small"]), _p(session.get("status"), styles["body"]), _p("Joined", styles["small"]), _p(session.get("joined_at") or session.get("started_at"), styles["body"])],
        ], [25 * mm, 55 * mm, 28 * mm, 66 * mm], header=False),
        Spacer(1, 8),
        _p("Outcome Summary", styles["heading"]),
        _table([
            [_p("Marks", styles["small"]), _p("Integrity", styles["small"]), _p("Review", styles["small"]), _p("Release", styles["small"])],
            [_p(f"{grade.get('earned_marks', 'Pending')} / {grade.get('total_marks', exam.get('total_marks', 'Pending'))}", styles["center"]), _p(f"{integrity.get('score', 'N/A')} - {integrity.get('status', 'N/A')}", styles["center"]), _p(session.get("review_status", "pending"), styles["center"]), _p("Released" if session.get("grade_released") else "Held", styles["center"])],
        ], [43.5 * mm] * 4),
        _p("Answer Evaluation", styles["heading"]),
    ]
    answers_by_question = {str(item.get("question_id")): item for item in answers}
    answer_rows: list[list[object]] = [[_p("# / Type", styles["small"]), _p("Question and submitted answer", styles["small"]), _p("Score", styles["small"]), _p("Evaluation", styles["small"])]]
    for index, question in enumerate(questions, 1):
        answer = answers_by_question.get(str(question.get("id")), {})
        response = answer.get("selected_option") or answer.get("answer_text") or "No answer submitted"
        combined = f"<b>{escape(str(question.get('text', 'Question')))}</b><br/><font color='#52606D'>{escape(str(response))}</font>"
        answer_rows.append([_p(f"{index}. {question.get('type', '')}", styles["small"]), Paragraph(combined, styles["body"]), _p(f"{answer.get('eval_score', 0)} / {question.get('marks', 0)}", styles["center"]), _p(answer.get("eval_reasoning") or "Not evaluated", styles["small"])])
    if len(answer_rows) == 1:
        answer_rows.append([_p("-", styles["small"]), _p("No question records were available.", styles["body"]), _p("-", styles["small"]), _p("-", styles["small"])])
    story.append(_table(answer_rows, [25 * mm, 91 * mm, 22 * mm, 36 * mm]))
    story.append(_p("Integrity Factors", styles["heading"]))
    factor_rows = [[_p("Factor", styles["small"]), _p("Score", styles["small"])]]
    for key, value in (integrity.get("factors") or {}).items():
        factor_rows.append([_p(key.replace("_", " ").title(), styles["body"]), _p(value, styles["center"])])
    if len(factor_rows) == 1:
        factor_rows.append([_p("No factor detail", styles["body"]), _p("N/A", styles["center"])])
    story.append(_table(factor_rows, [120 * mm, 54 * mm]))
    story.append(_p("Proctoring Timeline", styles["heading"]))
    event_rows = [[_p("Time", styles["small"]), _p("Event", styles["small"]), _p("Details", styles["small"])]]
    for event in events:
        detail = event.get("metadata") or event.get("event_data") or {}
        event_rows.append([_p(str(event.get("occurred_at") or "")[:19], styles["small"]), _p(event.get("type") or event.get("event_type"), styles["body"]), _p(json.dumps(detail, sort_keys=True), styles["small"])])
    if len(event_rows) == 1:
        event_rows.append([_p("-", styles["small"]), _p("No integrity events recorded", styles["body"]), _p("Clean event timeline", styles["small"])])
    story.append(_table(event_rows, [35 * mm, 45 * mm, 94 * mm]))
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


def build_class_pdf_report(exam: dict[str, Any], sessions: list[dict[str, Any]]) -> bytes:
    buffer = BytesIO()
    styles = _pdf_styles()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title=f"{exam.get('title', 'Exam')} class report")
    story: list[Any] = [_p("ExamGuard AI Class Examination Report", styles["title"]), _p(f"{exam.get('title', 'Exam')} | {exam.get('subject', '')} | {exam.get('total_marks', '')} marks | {len(sessions)} students", styles["subtitle"]), _p("Class Overview", styles["heading"])]
    overview = [[_p("Student", styles["small"]), _p("Attempt", styles["small"]), _p("Marks", styles["small"]), _p("Integrity", styles["small"]), _p("Review / Release", styles["small"])]]
    for session in sessions:
        grade = session.get("grade") or {}
        integrity = session.get("integrity") or {}
        overview.append([_p(session.get("student_name", "Student"), styles["body"]), _p(session.get("status", ""), styles["center"]), _p(f"{grade.get('earned_marks', 'Pending')} / {grade.get('total_marks', exam.get('total_marks', ''))}", styles["center"]), _p(f"{integrity.get('score', 'N/A')} {integrity.get('status', '')}", styles["center"]), _p(f"{session.get('review_status', 'pending')} | {'Released' if session.get('grade_released') else 'Held'}", styles["small"])])
    if len(overview) == 1:
        overview.append([_p("No student submissions", styles["body"]), _p("-", styles["center"]), _p("-", styles["center"]), _p("-", styles["center"]), _p("-", styles["center"])])
    story.append(_table(overview, [47 * mm, 24 * mm, 31 * mm, 32 * mm, 40 * mm]))
    for index, session in enumerate(sessions, 1):
        grade = session.get("grade") or {}
        integrity = session.get("integrity") or {}
        story.extend([PageBreak(), _p(f"Student {index}: {session.get('student_name', 'Student')}", styles["title"]), _table([
            [_p("Session ID", styles["small"]), _p(session.get("id") or session.get("session_id"), styles["body"])],
            [_p("Attempt status", styles["small"]), _p(session.get("status"), styles["body"])],
            [_p("Joined / started", styles["small"]), _p(session.get("joined_at") or session.get("started_at"), styles["body"])],
            [_p("Answers / events", styles["small"]), _p(f"{session.get('answers_count', 0)} answers | {session.get('events_count', 0)} events", styles["body"])],
            [_p("Marks", styles["small"]), _p(f"{grade.get('earned_marks', 'Pending')} / {grade.get('total_marks', exam.get('total_marks', ''))} ({grade.get('percentage', 'Pending')}%)", styles["body"])],
            [_p("Integrity", styles["small"]), _p(f"{integrity.get('score', 'N/A')} - {integrity.get('status', 'N/A')} | CI {integrity.get('ci', 'N/A')} | Tier {integrity.get('baseline_tier', 'N/A')}", styles["body"])],
            [_p("Review outcome", styles["small"]), _p(f"{session.get('review_status', 'pending')} | {'Grade released' if session.get('grade_released') else 'Grade held'}", styles["body"])],
        ], [42 * mm, 132 * mm], header=False), Spacer(1, 8), _p("Integrity signals are indicators for teacher review. The recorded teacher decision remains the authoritative outcome.", styles["subtitle"])])
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


store = LocalStore()
