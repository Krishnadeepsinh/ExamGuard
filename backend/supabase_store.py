"""Supabase-backed store for ExamGuard.

Uses the service-role key only on the FastAPI backend. Do not import this from
frontend code and do not expose these calls to the browser.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from urllib import error, parse, request
from uuid import uuid4

from backend.agents.material_ingestion_agent import chunk_text, detect_chapter, chunk_text_with_chapters, embed_text, rank_chunks
from backend.agents.llm_router import generate_grounded_questions, gemini_router
from backend.agents.evaluation_agent import grade_objective, grade_subjective
from backend.agents.orchestrator_agent import compute_integrity_score
from backend.agents.paper_config_agent import generate_join_code, validate_paper_config
from backend.agents.proctoring_agent import behavioral_score, has_critical_pattern, impact_for
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from backend.store import build_pdf_report


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseStore:
    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self.url = supabase_url.rstrip("/")
        self.key = service_role_key
        self.reports: dict[str, bytes] = {}

    def headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def rest(self, method: str, table: str, payload: Any = None, query: str = "") -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(f"{self.url}/rest/v1/{table}{query}", data=body, method=method, headers=self.headers())
        try:
            with request.urlopen(req, timeout=20) as response:
                data = response.read().decode("utf-8")
                return json.loads(data) if data else None
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(detail or exc.reason) from exc

    def auth_request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(
            f"{self.url}/auth/v1/{path}", data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = json.loads(exc.read().decode("utf-8", errors="ignore") or "{}")
            raise PermissionError(detail.get("msg") or detail.get("error_description") or "Authentication failed") from exc

    def verify_token(self, token: str) -> dict[str, Any]:
        req = request.Request(f"{self.url}/auth/v1/user", method="GET", headers={
            "apikey": self.key, "Authorization": f"Bearer {token}",
        })
        try:
            with request.urlopen(req, timeout=12) as response:
                auth_user = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise PermissionError("Invalid or expired access token") from exc
        profiles = self.rest("GET", "users", query=f"?id=eq.{auth_user['id']}")
        if not profiles and auth_user.get("email"):
            encoded_email = parse.quote(auth_user["email"], safe="")
            profiles = self.rest("GET", "users", query=f"?email=eq.{encoded_email}")
        if not profiles:
            raise PermissionError("User profile is missing")
        return profiles[0]

    def ensure_demo_teacher(self, email: str) -> dict[str, Any]:
        encoded = parse.quote(email, safe="")
        existing = self.rest("GET", "users", query=f"?email=eq.{encoded}")
        if existing:
            profile = existing[0]
            if profile.get("role") != "teacher":
                profile = self.rest("PATCH", "users", {"role": "teacher"}, query=f"?id=eq.{profile['id']}")[0]
            return profile
        return self.rest("POST", "users", {
            "id": str(uuid4()), "email": email, "display_name": "Demo Teacher",
            "institute_name": "ExamGuard Demo", "role": "teacher", "baseline_answer_count": 0,
        })[0]

    def login(self, email: str, password: str, role: str, display_name: str | None = None, signup: bool = False) -> dict[str, Any]:
        auth = self.auth_request("signup" if signup else "token?grant_type=password", {
            "email": email, "password": password,
            "data": {"role": role, "display_name": display_name or email.split("@")[0]},
        })
        auth_user = auth.get("user") or {}
        if not auth_user.get("id"):
            raise PermissionError("Check your email to confirm signup, then login")
        encoded = parse.quote(email, safe="")
        existing = self.rest("GET", "users", query=f"?email=eq.{encoded}")
        if existing:
            profile = existing[0]
            if profile["role"] != role:
                raise PermissionError(f"Account is registered as {profile['role']}")
        else:
            profile = self.rest("POST", "users", {
                "id": auth_user["id"], "email": email,
                "display_name": display_name or auth_user.get("user_metadata", {}).get("display_name") or email.split("@")[0],
                "role": role, "institute_name": "", "baseline_answer_count": 0,
            })[0]
        return {**profile, "access_token": auth.get("access_token", ""), "refresh_token": auth.get("refresh_token", "")}

    def request_password_reset(self, email: str) -> None:
        self.auth_request("recover", {"email": email})

    def confirm_password_reset(self, token: str, password: str) -> None:
        req = request.Request(
            f"{self.url}/auth/v1/user",
            data=json.dumps({"password": password}).encode("utf-8"),
            method="PUT",
            headers={"apikey": self.key, "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=20):
                return
        except error.HTTPError as exc:
            detail = json.loads(exc.read().decode("utf-8", errors="ignore") or "{}")
            raise PermissionError(detail.get("msg") or detail.get("error_description") or "Invalid or expired reset token") from exc

    def create_exam(self, teacher_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing_codes = {exam["join_code"] for exam in self.rest("GET", "exams", query="?select=join_code")}
        created = self.rest("POST", "exams", {
            "teacher_id": teacher_id,
            "title": payload["title"],
            "subject": payload["subject"],
            "duration_min": payload["duration_minutes"],
            "total_marks": payload["total_marks"],
            "join_code": generate_join_code(existing_codes),
            "status": "draft",
            "paper_config": {},
        })
        return self.normalize_exam(created[0])

    def clone_exam(self, exam_id: str) -> dict[str, Any]:
        source = self.get_exam(exam_id)
        clone = self.create_exam(source["teacher_id"], {
            "title": f"{source['title']} Copy",
            "subject": source.get("subject") or "Exam",
            "duration_minutes": source["duration_minutes"],
            "total_marks": source["total_marks"],
        })
        updated = self.rest("PATCH", "exams", {
            "paper_config": source.get("paper_config") or {},
            "config_validated": bool(source.get("paper_config")),
            "questions_generated": False,
            "status": "draft",
        }, query=f"?id=eq.{clone['id']}")[0]
        return self.normalize_exam(updated)

    def list_exams(self, teacher_id: str | None = None) -> list[dict[str, Any]]:
        query = f"?teacher_id=eq.{teacher_id}" if teacher_id else ""
        return [self.normalize_exam(exam) for exam in self.rest("GET", "exams", query=query)]

    def get_exam(self, exam_id: str) -> dict[str, Any]:
        rows = self.rest("GET", "exams", query=f"?id=eq.{exam_id}")
        if not rows:
            raise KeyError("exam not found")
        return self.normalize_exam(rows[0])

    def normalize_exam(self, exam: dict[str, Any]) -> dict[str, Any]:
        return {
            **exam,
            "duration_minutes": exam.get("duration_min", exam.get("duration_minutes")),
        }

    def add_material(self, exam_id: str, filename: str, content: bytes, source_type: str = "material") -> dict[str, Any]:
        text = self.extract_text(filename, content)
        chunks, chapter_topics = chunk_text_with_chapters(text, source_page=1, approx_tokens=384)
        if not chunks:
            raise ValueError("No readable text was found in the uploaded material.")
        
        chapter_counts = {}
        for tag, topics in chapter_topics.items():
            count = sum(1 for c in chunks if c.chapter_tag == tag)
            if count > 0:
                chapter_counts[tag] = {
                    "count": count,
                    "topics": topics
                }

        safe_name = "".join(char if char.isalnum() or char in {".", "-", "_"} else "_" for char in filename)
        storage_path = f"{exam_id}/{source_type}/{uuid4().hex}_{safe_name}"
        content_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if filename.lower().endswith(".docx") else "text/plain"
        upload_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type,
            "x-upsert": "false",
        }
        upload = request.Request(f"{self.url}/storage/v1/object/materials/{parse.quote(storage_path, safe='/')}", data=content, method="POST", headers=upload_headers)
        try:
            with request.urlopen(upload, timeout=60):
                pass
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Material storage upload failed: {detail or exc.reason}") from exc

        material = self.rest("POST", "materials", {
            "exam_id": exam_id,
            "filename": filename,
            "storage_path": storage_path,
            "status": "ready",
            "chunk_count": len(chunks),
            "chapter_counts": chapter_counts,
        })[0]
        chunk_rows = [
            {
                "exam_id": exam_id,
                "material_id": material["id"],
                "material_filename": filename,
                "chunk_text": item.chunk_text,
                "chapter_tag": item.chapter_tag,
                "source_page": item.source_page,
                "chunk_index": item.chunk_index,
                "embedding": embed_text(item.chunk_text),
            }
            for item in chunks
        ]
        for start in range(0, len(chunk_rows), 500):
            self.rest("POST", "material_chunks", chunk_rows[start:start + 500])
        return {**material, "source_type": source_type}

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

    def list_materials(self, exam_id: str) -> list[dict[str, Any]]:
        return [self.normalize_material(item) for item in self.rest("GET", "materials", query=f"?exam_id=eq.{exam_id}")]

    def get_material(self, material_id: str) -> dict[str, Any]:
        rows = self.rest("GET", "materials", query=f"?id=eq.{material_id}")
        if not rows:
            raise KeyError("material not found")
        return self.normalize_material(rows[0])

    def normalize_material(self, material: dict[str, Any]) -> dict[str, Any]:
        parts = str(material.get("storage_path", "")).split("/")
        source_type = parts[1] if len(parts) > 2 and parts[1] in {"syllabus", "material"} else "material"
        return {**material, "source_type": source_type}

    def configure_exam(self, exam_id: str, config: dict[str, Any]) -> dict[str, Any]:
        current = self.get_exam(exam_id)
        if current.get("status") in {"active", "paused", "ended", "archived"}:
            raise ValueError("Activated papers are immutable. Clone this exam to create a new version.")
        material_ids = config.get("material_ids") or ([config.get("material_id")] if config.get("material_id") else [])
        material_id = material_ids[0] if material_ids else None
        materials = [self.get_material(item) for item in material_ids]
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
        exam = self.rest("PATCH", "exams", {
            "total_marks": config["total_marks"],
            "paper_config": config,
            "config_validated": True,
        }, query=f"?id=eq.{exam_id}")[0]
        return {"status": "saved", "exam": self.normalize_exam(exam), "validation": validation}

    def generate_questions(self, exam_id: str) -> dict[str, Any]:
        exam = self.get_exam(exam_id)
        if exam.get("status") in {"active", "paused", "ended", "archived"}:
            raise ValueError("Activated papers are immutable. Clone this exam to regenerate questions.")
        existing_sessions = self.rest("GET", "exam_sessions", query=f"?exam_id=eq.{exam_id}&select=id&limit=1")
        if existing_sessions:
            raise ValueError("Cannot regenerate a paper after students have joined. Clone the exam to create a new version.")
        config = exam.get("paper_config") or {}
        material_ids = config.get("material_ids") or ([config.get("material_id")] if config.get("material_id") else [])
        if not material_ids:
            raise ValueError("Upload syllabus or study material before generating questions.")
        chunks = self.rest("GET", "material_chunks", query=f"?exam_id=eq.{exam_id}")
        if not chunks:
            raise ValueError("Uploaded material has no usable chunks. Re-upload a readable PDF, DOCX, or TXT file.")
        questions: list[dict[str, Any]] = []
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
            # Generate a complete ordinary section in one provider request to
            # stay below browser/proxy timeouts on Render's free instances.
            batch_size = 25
            for batch_start in range(0, section["count"], batch_size):
                batch_count = min(batch_size, section["count"] - batch_start)
                try:
                    generated_items.extend(generate_grounded_questions(
                        section["type"], batch_count,
                        section.get("level") or config["overall_level"], section["bloom"],
                        section["marks_each"], matching[batch_start:batch_start + 8] or matching[:8],
                    ))
                except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                    raise RuntimeError(
                        f"Question generation failed quality checks for section {section['id']}. "
                        "No placeholder paper was saved; retry generation."
                    ) from exc

            for index in range(section["count"]):
                if matching:
                    source = matching[index % len(matching)]
                    source_chunk_ids = [source["id"]]
                    groundedness_score = 0.84
                else:
                    source = {"chunk_text": ""}
                    source_chunk_ids = []
                    groundedness_score = 0.50
                    
                scope_label = chapter_tag
                if topic_tag and topic_tag != "All topics":
                    scope_label = f"{chapter_tag} ({topic_tag})"
                elif chapter_tag == "All syllabus":
                    scope_label = "Complete Syllabus"
                    
                generated = generated_items[index] if index < len(generated_items) else {}
                if not generated:
                    raise RuntimeError(f"Question generation returned an empty item for section {section['id']}.")
                source_number = generated.get("source_number", 1)
                try:
                    source_number = max(1, min(int(source_number), len(matching)))
                except (TypeError, ValueError):
                    source_number = 1
                if matching:
                    source = matching[(index + source_number - 1) % len(matching)]
                    source_chunk_ids = [source["id"]]
                options = generated.get("options") if isinstance(generated.get("options"), list) else []
                questions.append({
                    "exam_id": exam_id,
                    "section_label": section["id"],
                    "section_index": section_index,
                    "question_index": index,
                    "question_text": str(generated["text"]),
                    "question_type": section["type"],
                    "options": options,
                    "correct_answer": str(generated["correct_answer"]),
                    "marks": section["marks_each"],
                    "blooms_level": section["bloom"],
                    "chapter_tag": chapter_tag,
                    "source_chunk_ids": source_chunk_ids,
                    "groundedness_score": groundedness_score,
                    "low_groundedness": groundedness_score <= 0.72,
                    "generation_attempts": 1 if groundedness_score > 0.72 else 3,
                    "teacher_modified": False,
                })
        self.rest("DELETE", "questions", query=f"?exam_id=eq.{exam_id}")
        if questions:
            created = self.rest("POST", "questions", questions)
        else:
            created = []
        self.rest("PATCH", "exams", {"questions_generated": True, "status": "draft"}, query=f"?id=eq.{exam_id}")
        return {
            "status": "generated", "count": len(created),
            "questions": [self.normalize_question(item) for item in created],
            "llm": gemini_router.status(), "fallback_count": 0,
        }

    def normalize_question(self, question: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": question["id"],
            "exam_id": question["exam_id"],
            "section_id": question["section_label"],
            "type": question["question_type"],
            "text": question["question_text"],
            "options": question.get("options") or [],
            "correct_answer": question.get("correct_answer"),
            "marks": question["marks"],
            "bloom_level": question.get("blooms_level"),
            "chapter_tag": question.get("chapter_tag"),
            "source_chunk_ids": question.get("source_chunk_ids") or [],
            "groundedness": question.get("groundedness_score"),
            "teacher_modified": question.get("teacher_modified", False),
        }

    def exam_questions(self, exam_id: str) -> list[dict[str, Any]]:
        self.get_exam(exam_id)
        rows = self.rest("GET", "questions", query=f"?exam_id=eq.{exam_id}&order=section_index.asc,question_index.asc")
        return [self.normalize_question(row) for row in rows]

    def activate_exam(self, exam_id: str) -> dict[str, Any]:
        questions = self.rest("GET", "questions", query=f"?exam_id=eq.{exam_id}")
        if not questions:
            raise ValueError("generate questions before activation")
        current = self.get_exam(exam_id)
        if current.get("status") == "active":
            return current
        version = int(current.get("paper_version") or 0) + 1
        snapshot = {"version": version, "config": current.get("paper_config") or {}, "questions": questions, "captured_at": utc_now()}
        return self.normalize_exam(self.rest("PATCH", "exams", {"status": "active", "activated_at": utc_now(), "paper_version": version, "paper_snapshot": snapshot}, query=f"?id=eq.{exam_id}")[0])

    def schedule_exam(self, exam_id: str, scheduled_start_at: str) -> dict[str, Any]:
        questions = self.rest("GET", "questions", query=f"?exam_id=eq.{exam_id}&select=id&limit=1")
        if not questions:
            raise ValueError("Generate and review questions before scheduling the exam.")
        current = self.get_exam(exam_id)
        if current.get("status") not in {"draft", "scheduled"}:
            raise ValueError("Only a draft paper can be scheduled.")
        return self.normalize_exam(self.rest("PATCH", "exams", {"status": "scheduled", "scheduled_start_at": scheduled_start_at}, query=f"?id=eq.{exam_id}")[0])

    def end_exam(self, exam_id: str) -> dict[str, Any]:
        ended_at = utc_now()
        exam = self.rest("PATCH", "exams", {"status": "ended", "ended_at": ended_at}, query=f"?id=eq.{exam_id}")[0]
        self.rest("PATCH", "exam_sessions", {"status": "ended", "ended_at": ended_at}, query=f"?exam_id=eq.{exam_id}&status=neq.ended")
        return self.normalize_exam(exam)

    def join_session(self, join_code: str, student_name: str, email: str | None) -> dict[str, Any]:
        exams = self.rest("GET", "exams", query=f"?join_code=eq.{join_code}")
        if not exams:
            raise KeyError("Invalid join code.")
        if exams[0]["status"] == "scheduled" and exams[0].get("scheduled_start_at"):
            scheduled = datetime.fromisoformat(str(exams[0]["scheduled_start_at"]).replace("Z", "+00:00"))
            if scheduled <= datetime.now(timezone.utc):
                exams[0] = self.activate_exam(str(exams[0]["id"]))
        if exams[0]["status"] != "active":
            raise PermissionError(f"Exam is {exams[0]['status']} and is not accepting students.")
        student_email = email or f"{student_name.lower().replace(' ', '.')}@student.local"
        encoded_email = parse.quote(student_email, safe="")
        users = self.rest("GET", "users", query=f"?email=eq.{encoded_email}&role=eq.student")
        user = users[0] if users else self.rest("POST", "users", {
            "email": student_email, "display_name": student_name, "role": "student",
            "institute_name": "", "baseline_answer_count": 0,
        })[0]
        existing = self.rest("GET", "exam_sessions", query=f"?exam_id=eq.{exams[0]['id']}&student_id=eq.{user['id']}")
        if existing:
            return self.normalize_session(existing[0], student_name)
        factors = {"behavioral": 100, "perplexity": 100, "stylometric": 100, "answer_quality": 100, "time_anomaly": 100}
        integrity = compute_integrity_score(factors, baseline_tier=3)
        session = self.rest("POST", "exam_sessions", {
            "exam_id": exams[0]["id"],
            "student_id": user["id"],
            "status": "joined",
            "consent_given": False,
            "liveness_verified": False,
            "integrity_state": integrity["status"],
            "integrity_score": integrity["score"],
            "integrity_ci": integrity["ci"],
            "baseline_tier": integrity["baseline_tier"],
            "integrity_factors": factors,
        })[0]
        return self.normalize_session(session, student_name)

    def student_sessions(self, student_id: str) -> list[dict[str, Any]]:
        rows = self.rest("GET", "exam_sessions", query=f"?student_id=eq.{student_id}&order=created_at.desc")
        return [self.get_session_result(str(row["id"])) for row in rows]

    def normalize_session(self, session: dict[str, Any], student_name: str | None = None) -> dict[str, Any]:
        if student_name is None:
            user = self.rest("GET", "users", query=f"?id=eq.{session['student_id']}")
            student_name = user[0]["display_name"] if user else "Student"
        return {
            "id": session["id"],
            "student_id": session["student_id"],
            "student_name": student_name,
            "exam_id": session["exam_id"],
            "status": session["status"],
            "consent": session.get("consent_given", False),
            "liveness": session.get("liveness_verified", False),
            "integrity": {
                "score": session.get("integrity_score"),
                "status": session.get("integrity_state"),
                "ci": session.get("integrity_ci"),
                "baseline_tier": session.get("baseline_tier"),
                "factors": session.get("integrity_factors") or {},
            },
            "review_status": session.get("review_status"),
            "grade_released": session.get("grade_released", False),
            "locked_for_review": session.get("locked_for_review", False),
            "expires_at": session.get("expires_at"),
        }

    def require_session(self, session_id: str) -> dict[str, Any]:
        rows = self.rest("GET", "exam_sessions", query=f"?id=eq.{session_id}")
        if not rows:
            raise KeyError("session not found")
        return rows[0]

    def update_session(self, session_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        return self.rest("PATCH", "exam_sessions", patch, query=f"?id=eq.{session_id}")[0]

    def session_questions(self, session_id: str) -> list[dict[str, Any]]:
        session = self.require_session(session_id)
        rows = self.rest("GET", "questions", query=f"?exam_id=eq.{session['exam_id']}")
        return [self.normalize_question(row) for row in rows]

    def save_answer(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = {
            "session_id": session_id,
            "question_id": payload["question_id"],
            "answer_text": payload.get("answer_text"),
            "selected_option": payload.get("selected_option"),
            "time_spent_seconds": payload.get("time_spent_seconds", 0),
            "idempotency_key": payload.get("idempotency_key"),
        }
        if payload.get("idempotency_key"):
            encoded = parse.quote(str(payload["idempotency_key"]), safe="")
            duplicate = self.rest("GET", "answers", query=f"?session_id=eq.{session_id}&idempotency_key=eq.{encoded}")
            if duplicate:
                return duplicate[0]
        existing = self.rest("GET", "answers", query=f"?session_id=eq.{session_id}&question_id=eq.{payload['question_id']}")
        created = self.rest("PATCH", "answers", row, query=f"?id=eq.{existing[0]['id']}") if existing else self.rest("POST", "answers", row)
        return created[0]

    def evaluate_session(self, session_id: str) -> dict[str, Any]:
        questions = {item["id"]: item for item in self.session_questions(session_id)}
        answers = self.rest("GET", "answers", query=f"?session_id=eq.{session_id}") or []
        total = sum(float(item.get("marks", 0)) for item in questions.values())
        earned = 0.0
        for answer in answers:
            question = questions.get(answer["question_id"])
            if not question:
                continue
            response = str(answer.get("selected_option") or answer.get("answer_text") or "")
            grader = grade_objective if question.get("type") in {"MCQ", "True/False", "Fill Blank"} else grade_subjective
            result = grader(response, str(question.get("correct_answer") or ""), int(question.get("marks", 0)))
            self.rest("PATCH", "answers", {"eval_score": result["score"], "eval_reasoning": result["reasoning"]}, query=f"?id=eq.{answer['id']}")
            earned += float(result["score"])
        return {"earned_marks": round(earned, 2), "total_marks": round(total, 2), "percentage": round(earned / total * 100, 2) if total else 0}

    def exam_students(self, exam_id: str) -> list[dict[str, Any]]:
        rows = self.rest(
            "GET",
            "exam_sessions",
            query=(
                f"?exam_id=eq.{exam_id}"
                "&select=*,users!exam_sessions_student_id_fkey(display_name),"
                "answers(eval_score),integrity_events(count),"
                "integrity_appeals(student_response,submitted_at,deadline_at)"
            ),
        )
        result = []
        exam = self.get_exam(exam_id)
        for row in rows:
            user = row.pop("users", None) or {}
            answers = row.pop("answers", None) or []
            events = row.pop("integrity_events", None) or []
            appeals = row.pop("integrity_appeals", None) or []
            session = self.normalize_session(row, user.get("display_name") or "Student")
            session["answers_count"] = len(answers)
            earned = round(sum(float(answer.get("eval_score") or 0) for answer in answers), 2)
            total = float(exam.get("total_marks") or 0)
            session["grade"] = {"earned_marks": earned, "total_marks": total, "percentage": round(earned / total * 100, 2) if total else 0}
            session["events_count"] = int(events[0].get("count", 0)) if events else 0
            session["joined_at"] = row.get("started_at") or row.get("created_at")
            if appeals:
                appeal = appeals[0] if isinstance(appeals, list) else appeals
                session["appeal"] = {
                    "response": appeal.get("student_response", ""),
                    "submitted_at": appeal.get("submitted_at"),
                    "deadline_at": appeal.get("deadline_at"),
                }
            result.append(session)
        return result

    def log_integrity_event(self, session_id: str, event_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
        severity = "warning" if event_type in {"tab_hidden", "window_blur", "fullscreen_exit", "paste_detected"} else "info"
        prior_rows = self.rest("GET", "integrity_events", query=f"?session_id=eq.{session_id}&select=sequence_number,event_hash&order=sequence_number.desc&limit=1") or []
        sequence = int(prior_rows[0].get("sequence_number") or 0) + 1 if prior_rows else 1
        previous_hash = str(prior_rows[0].get("event_hash") or "") if prior_rows else ""
        occurred_at = utc_now()
        canonical = json.dumps({"session_id": session_id, "sequence": sequence, "type": event_type, "metadata": metadata, "occurred_at": occurred_at}, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(f"{previous_hash}:{canonical}".encode()).hexdigest()
        created = self.rest("POST", "integrity_events", {
            "session_id": session_id,
            "event_type": event_type,
            "event_data": metadata,
            "score_impact": impact_for(event_type, metadata),
            "severity": severity,
            "occurred_at": occurred_at,
            "sequence_number": sequence,
            "previous_hash": previous_hash or None,
            "event_hash": event_hash,
        })[0]
        rows = self.rest("GET", "integrity_events", query=f"?session_id=eq.{session_id}&select=event_type,event_data") or []
        event_types = [{"type": row["event_type"], "metadata": row.get("event_data") or {}} for row in rows]
        behavioral = behavioral_score(event_types)
        session = self.require_session(session_id)
        prior_factors = session.get("integrity_factors") or {}
        factors = {
            "behavioral": behavioral,
            "perplexity": float(prior_factors.get("perplexity", 100)),
            "stylometric": float(prior_factors.get("stylometric", 100)),
            "answer_quality": float(prior_factors.get("answer_quality", 100)),
            "time_anomaly": float(prior_factors.get("time_anomaly", 100)),
        }
        baseline_tier = int(session.get("baseline_tier") or 3)
        result = compute_integrity_score(factors, baseline_tier=baseline_tier)
        critical_pattern = has_critical_pattern(event_types)
        if critical_pattern:
            result = {**result, "score": min(float(result["score"]), 45.0), "status": "FLAGGED"}
        patch: dict[str, Any] = {"integrity_score": result["score"], "integrity_state": result["status"], "integrity_ci": result["ci"], "integrity_factors": factors}
        if result["status"] == "FLAGGED":
            patch["review_status"] = "awaiting_response"
        if critical_pattern:
            patch["locked_for_review"] = True
        self.update_session(session_id, patch)
        return {**created, "integrity": result}

    def generate_report_pdf(self, session_id: str) -> bytes:
        session_row = self.require_session(session_id)
        session = self.normalize_session(session_row)
        questions = self.session_questions(session_id)
        answers = self.rest("GET", "answers", query=f"?session_id=eq.{session_id}") or []
        events = self.rest("GET", "integrity_events", query=f"?session_id=eq.{session_id}") or []
        
        data = build_pdf_report(session, questions, answers, events)
        self.reports[session_id] = data
        return data

    def appeal_deadline(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    def delete_exam(self, exam_id: str) -> None:
        self.get_exam(exam_id)
        sessions = self.rest("GET", "exam_sessions", query=f"?exam_id=eq.{exam_id}") or []
        for s in sessions:
            self.rest("DELETE", "integrity_appeals", query=f"?session_id=eq.{s['id']}")
            self.rest("DELETE", "answers", query=f"?session_id=eq.{s['id']}")
            self.rest("DELETE", "integrity_events", query=f"?session_id=eq.{s['id']}")
        self.rest("DELETE", "exam_sessions", query=f"?exam_id=eq.{exam_id}")
        self.rest("DELETE", "material_chunks", query=f"?exam_id=eq.{exam_id}")
        self.rest("DELETE", "materials", query=f"?exam_id=eq.{exam_id}")
        self.rest("DELETE", "questions", query=f"?exam_id=eq.{exam_id}")
        self.rest("DELETE", "exams", query=f"?id=eq.{exam_id}")

    def clone_exam(self, exam_id: str) -> dict[str, Any]:
        source = self.get_exam(exam_id)
        cloned = self.create_exam(source["teacher_id"], {
            "title": f"{source['title']} (Copy)",
            "subject": source["subject"],
            "duration_minutes": source["duration_min"],
            "total_marks": source["total_marks"],
        })
        if source.get("paper_config"):
            self.rest("PATCH", "exams", {
                "paper_config": source["paper_config"],
                "config_validated": source.get("config_validated", False)
            }, query=f"?id=eq.{cloned['id']}")
            cloned["paper_config"] = source["paper_config"]
        return cloned

    def delete_material(self, material_id: str) -> None:
        material = self.get_material(material_id)
        storage_path = material.get("storage_path")
        if storage_path:
            delete_headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
            delete_request = request.Request(f"{self.url}/storage/v1/object/materials/{parse.quote(storage_path, safe='/')}", method="DELETE", headers=delete_headers)
            try:
                with request.urlopen(delete_request, timeout=20):
                    pass
            except error.HTTPError as exc:
                if exc.code != 404:
                    detail = exc.read().decode("utf-8", errors="ignore")
                    raise RuntimeError(f"Material storage delete failed: {detail or exc.reason}") from exc
        self.rest("DELETE", "materials", query=f"?id=eq.{material_id}")

    def get_session_result(self, session_id: str) -> dict[str, Any]:
        session_row = self.require_session(session_id)
        session = self.normalize_session(session_row)
        answers = self.rest("GET", "answers", query=f"?session_id=eq.{session_id}") or []
        earned = round(sum(float(answer.get("eval_score") or 0) for answer in answers), 2)
        questions = self.session_questions(session_id)
        total = round(sum(float(question.get("marks") or 0) for question in questions), 2)
        return {
            "session_id": session_id,
            "student_name": session.get("student_name", ""),
            "status": session.get("status", ""),
            "integrity": session.get("integrity", {}),
            "review_status": session.get("review_status", "none"),
            "grade_released": session.get("grade_released", False),
            "answers_count": len(answers),
            "answers": answers,
            "grade": ({"earned_marks": earned, "total_marks": total, "percentage": round(earned / total * 100, 2) if total else 0} if session.get("grade_released") else None),
        }

    def pause_exam(self, exam_id: str) -> dict[str, Any]:
        exam = self.get_exam(exam_id)
        if exam["status"] != "active":
            raise ValueError("only active exams can be paused")
        updated = self.rest("PATCH", "exams", {"status": "paused"}, query=f"?id=eq.{exam_id}")[0]
        return self.normalize_exam(updated)

    def resume_exam(self, exam_id: str) -> dict[str, Any]:
        exam = self.get_exam(exam_id)
        if exam["status"] != "paused":
            raise ValueError("only paused exams can be resumed")
        updated = self.rest("PATCH", "exams", {"status": "active"}, query=f"?id=eq.{exam_id}")[0]
        return self.normalize_exam(updated)

    def submit_appeal(self, session_id: str, response: str) -> dict[str, Any]:
        deadline = self.appeal_deadline()
        appeal = self.rest("POST", "integrity_appeals", {
            "session_id": session_id,
            "student_response": response,
            "submitted_at": deadline,
            "deadline_at": deadline,
        })[0]
        self.update_session(session_id, {"review_status": "awaiting_response"})
        return {"response": appeal["student_response"], "submitted_at": appeal["submitted_at"], "status": "submitted"}

    def teacher_decision(self, session_id: str, decision: str, teacher_note: str) -> dict[str, Any]:
        try:
            self.rest("PATCH", "integrity_appeals", {"teacher_note": teacher_note}, query=f"?session_id=eq.{session_id}")
        except Exception:
            pass
        updated = self.update_session(session_id, {
            "teacher_decision": "cleared" if decision == "clear" else "confirmed_flag",
            "decision_at": self.appeal_deadline(),
            "grade_released": True,
            "review_status": "decided",
        })
        return self.normalize_session(updated)

    def save_settings(self, user_id: str, display_name: str, institute_name: str) -> dict[str, Any]:
        updated = self.rest("PATCH", "users", {
            "display_name": display_name,
            "institute_name": institute_name,
        }, query=f"?id=eq.{user_id}")
        if not updated:
            raise KeyError("user not found")
        return updated[0]
