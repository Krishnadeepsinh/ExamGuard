"""Working local FastAPI app for ExamGuard AI v6.

This implements the real API contract with an in-memory store. It is suitable
for local demos and frontend integration while Supabase/Redis/Gemini are wired.
"""

from __future__ import annotations

import csv
import io
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.agents.constants import FACTOR_WEIGHTS
from backend.agents.graph import AGENT_NODES
from backend.config import settings
from backend.redis_client import redis_hot_state
from backend.store import store as local_store

if settings.supabase_enabled:
    from backend.supabase_store import SupabaseStore

    store = SupabaseStore(settings.supabase_url, settings.supabase_service_role_key)
else:
    store = local_store

# --- Rate Limiter -----------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="ExamGuard AI v6", version="6.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://examguard.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models --------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    role: Literal["teacher", "student"]
    display_name: str | None = Field(default=None, min_length=3)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("valid email is required")
        return value


class ExamCreateRequest(BaseModel):
    teacher_id: str
    title: str = Field(min_length=3, max_length=120)
    subject: str = Field(min_length=2, max_length=80)
    duration_minutes: int = Field(ge=10, le=300)
    total_marks: int = Field(ge=10, le=300)


class SectionConfig(BaseModel):
    id: str
    type: Literal["MCQ", "Short Answer", "Long Answer", "Fill Blank", "True/False", "Essay"]
    count: int = Field(ge=1, le=100)
    marks_each: int = Field(ge=1, le=20)
    bloom: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    chapter_tag: str = Field(min_length=2)
    level: Literal["Use overall", "Easy", "Standard", "Challenging"] = "Use overall"


class PaperConfigRequest(BaseModel):
    material_id: str
    total_marks: int = Field(ge=10, le=300)
    overall_level: Literal["Easy", "Standard", "Challenging"]
    paper_mode: Literal["MCQ only", "MCQ + QA", "Mixed"]
    sections: list[SectionConfig] = Field(min_length=1)


class JoinRequest(BaseModel):
    join_code: str = Field(min_length=6, max_length=6)
    student_name: str = Field(min_length=3, max_length=80)
    email: str | None = None

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        if value and ("@" not in value or "." not in value.rsplit("@", 1)[-1]):
            raise ValueError("valid email is required")
        return value


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(default="", max_length=8000)
    selected_option: str | None = None
    time_spent_seconds: int = Field(default=0, ge=0, le=10800)


class AppealRequest(BaseModel):
    response: str = Field(min_length=40, max_length=3500)


class DecisionRequest(BaseModel):
    decision: Literal["clear", "confirm_flag"]
    teacher_note: str = Field(min_length=12, max_length=1200)


class ProctoringEventRequest(BaseModel):
    event_type: str
    metadata: dict[str, object] = Field(default_factory=dict)


class SettingsRequest(BaseModel):
    display_name: str = Field(min_length=3, max_length=80)
    institute_name: str = Field(min_length=3, max_length=120)
    email_on_flag: bool = True


# --- Helper ------------------------------------------------------------------


def _get_session_field(session: dict, field: str) -> object:
    """Safely get session fields that may differ between local/supabase stores."""
    if field == "consent":
        return session.get("consent", session.get("consent_given", False))
    if field == "liveness":
        return session.get("liveness", session.get("liveness_verified", False))
    return session.get(field)


# --- Health ------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": "6.0",
        "agents": len(AGENT_NODES),
        "factor_weights": FACTOR_WEIGHTS,
        "store": "supabase" if settings.supabase_enabled else "local",
        "redis": "upstash" if settings.redis_enabled else "disabled",
    }


# --- Auth --------------------------------------------------------------------


@app.post("/api/v1/auth/login")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest) -> dict[str, object]:
    user = store.login(payload.email, payload.role, payload.display_name)
    return {"user": user, "token": f"local-{user['id']}"}


@app.post("/api/v1/auth/signup")
@limiter.limit("5/minute")
def signup(request: Request, payload: LoginRequest) -> dict[str, object]:
    user = store.login(payload.email, payload.role, payload.display_name)
    return {"user": user, "token": f"local-{user['id']}"}


@app.post("/api/v1/auth/reset-request")
@limiter.limit("3/minute")
def reset_request(request: Request, payload: dict[str, str]) -> dict[str, str]:
    if "email" not in payload:
        raise HTTPException(status_code=422, detail="email is required")
    return {"status": "reset_link_created_local"}


@app.post("/api/v1/auth/reset-confirm")
@limiter.limit("3/minute")
def reset_confirm(request: Request, payload: dict[str, str]) -> dict[str, str]:
    if len(payload.get("password", "")) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    return {"status": "password_updated_local"}


# --- Exams -------------------------------------------------------------------


@app.post("/api/v1/exams")
@limiter.limit("20/minute")
def create_exam(request: Request, payload: ExamCreateRequest) -> dict[str, object]:
    if hasattr(store, "users") and payload.teacher_id not in store.users:
        raise HTTPException(status_code=404, detail="teacher not found")
    return store.create_exam(payload.teacher_id, payload.model_dump())


@app.get("/api/v1/exams")
def list_exams(teacher_id: str | None = None) -> list[dict[str, object]]:
    if hasattr(store, "list_exams"):
        return store.list_exams(teacher_id)
    exams = list(store.exams.values())
    if teacher_id:
        exams = [exam for exam in exams if exam["teacher_id"] == teacher_id]
    return exams


@app.get("/api/v1/exams/{exam_id}")
def get_exam(exam_id: str) -> dict[str, object]:
    if hasattr(store, "get_exam"):
        try:
            return store.get_exam(exam_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="exam not found") from exc
    if exam_id not in store.exams:
        raise HTTPException(status_code=404, detail="exam not found")
    return store.exams[exam_id]


@app.delete("/api/v1/exams/{exam_id}")
def delete_exam(exam_id: str) -> dict[str, str]:
    """Delete an exam and all associated data."""
    try:
        store.delete_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    return {"status": "deleted"}


@app.post("/api/v1/exams/{exam_id}/clone")
def clone_exam(exam_id: str) -> dict[str, object]:
    """Clone an exam with a new join code."""
    try:
        return store.clone_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc


@app.put("/api/v1/exams/{exam_id}/paper-config")
def save_paper_config(exam_id: str, payload: PaperConfigRequest) -> dict[str, object]:
    get_exam(exam_id)
    material_status(payload.material_id)
    result = store.configure_exam(exam_id, payload.model_dump())
    if result["status"] == "invalid":
        raise HTTPException(status_code=422, detail=result["errors"])
    return result


@app.post("/api/v1/exams/{exam_id}/generate")
@limiter.limit("5/minute")
def generate_paper(request: Request, exam_id: str) -> dict[str, object]:
    exam = get_exam(exam_id)
    if not exam.get("paper_config"):
        raise HTTPException(status_code=422, detail="paper config must be saved before generation")
    return store.generate_questions(exam_id)


@app.post("/api/v1/exams/{exam_id}/activate")
def activate_exam(exam_id: str) -> dict[str, object]:
    try:
        return store.activate_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc


@app.post("/api/v1/exams/{exam_id}/pause")
def pause_exam(exam_id: str) -> dict[str, object]:
    """Pause an active exam — freezes all student timers."""
    try:
        return store.pause_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/exams/{exam_id}/resume")
def resume_exam(exam_id: str) -> dict[str, object]:
    """Resume a paused exam."""
    try:
        return store.resume_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/exams/{exam_id}/end")
def end_exam(exam_id: str) -> dict[str, object]:
    try:
        return store.end_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc


@app.get("/api/v1/exams/{exam_id}/students")
def exam_students(exam_id: str) -> list[dict[str, object]]:
    if hasattr(store, "exam_students"):
        return store.exam_students(exam_id)
    return [session for session in store.sessions.values() if session["exam_id"] == exam_id]


@app.get("/api/v1/exams/{exam_id}/materials")
def exam_materials(exam_id: str) -> list[dict[str, object]]:
    if hasattr(store, "list_materials"):
        try:
            return store.list_materials(exam_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="exam not found") from exc
    if exam_id not in store.exams:
        raise HTTPException(status_code=404, detail="exam not found")
    return [
        {key: value for key, value in material.items() if key != "chunks"}
        for material in store.materials.values()
        if material["exam_id"] == exam_id
    ]


@app.get("/api/v1/exams/{exam_id}/reports")
def exam_reports(exam_id: str) -> dict[str, object]:
    sessions = exam_students(exam_id)
    return {
        "exam_id": exam_id,
        "reports_ready": len(sessions),
        "students": sessions,
        "average_integrity": round(sum(s["integrity"]["score"] for s in sessions) / len(sessions), 2) if sessions else 0,
    }


@app.get("/api/v1/exams/{exam_id}/reports/csv")
def exam_reports_csv(exam_id: str) -> StreamingResponse:
    """Export exam reports as CSV download."""
    sessions = exam_students(exam_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_name", "student_id", "integrity_score", "integrity_status", "status", "review_status", "grade_released"])
    for s in sessions:
        integrity = s.get("integrity", {})
        writer.writerow([
            s.get("student_name", ""),
            s.get("student_id", ""),
            integrity.get("score", ""),
            integrity.get("status", ""),
            s.get("status", ""),
            s.get("review_status", ""),
            s.get("grade_released", False),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=examguard_{exam_id}_report.csv"},
    )


@app.get("/api/v1/exams/{exam_id}/reports/summary")
def exam_summary(exam_id: str) -> dict[str, object]:
    """Summary statistics for an exam."""
    sessions = exam_students(exam_id)
    if not sessions:
        return {"exam_id": exam_id, "total_students": 0, "average_integrity": 0, "status_counts": {}, "appeals_open": 0}
    scores = [s["integrity"]["score"] for s in sessions if s.get("integrity", {}).get("score") is not None]
    status_counts: dict[str, int] = {}
    appeals_open = 0
    for s in sessions:
        st = s.get("integrity", {}).get("status", "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1
        if s.get("review_status") in ("awaiting_response", "appeal_submitted"):
            appeals_open += 1
    return {
        "exam_id": exam_id,
        "total_students": len(sessions),
        "average_integrity": round(sum(scores) / len(scores), 2) if scores else 0,
        "min_integrity": min(scores) if scores else 0,
        "max_integrity": max(scores) if scores else 0,
        "status_counts": status_counts,
        "appeals_open": appeals_open,
    }


@app.get("/api/v1/exams/{exam_id}/live-events")
def live_events(exam_id: str) -> dict[str, object]:
    return {
        "exam_id": exam_id,
        "redis": "upstash" if settings.redis_enabled else "disabled",
        "events": redis_hot_state.list_events(f"exam:{exam_id}:events") if settings.redis_enabled else [],
    }


# --- Materials ---------------------------------------------------------------


@app.post("/api/v1/materials/upload")
@limiter.limit("10/minute")
async def upload_material(request: Request, exam_id: str, file: UploadFile = File(...)) -> dict[str, object]:
    get_exam(exam_id)
    if not file.filename:
        raise HTTPException(status_code=422, detail="filename is required")
    if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=422, detail="only PDF, DOCX, or TXT files are allowed")
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="material file must be 50MB or smaller")
    return store.add_material(exam_id, file.filename, content)


@app.get("/api/v1/materials/{material_id}/status")
def material_status(material_id: str) -> dict[str, object]:
    try:
        material = store.get_material(material_id)
        return {key: value for key, value in material.items() if key != "chunks"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="material not found") from exc


@app.delete("/api/v1/materials/{material_id}")
def delete_material(material_id: str) -> dict[str, str]:
    """Delete uploaded material."""
    try:
        store.delete_material(material_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="material not found") from exc
    return {"status": "deleted"}


# --- Sessions ----------------------------------------------------------------


@app.post("/api/v1/sessions/join")
@limiter.limit("15/minute")
def join_session(request: Request, payload: JoinRequest) -> dict[str, object]:
    try:
        session = store.join_session(payload.join_code.upper(), payload.student_name, str(payload.email) if payload.email else None)
        redis_hot_state.set_json(f"session:{session['id']}:state", session, ttl_seconds=10800)
        redis_hot_state.push_event(f"exam:{session['exam_id']}:events", {"type": "student_joined", "session_id": session["id"], "student_name": session["student_name"]}, ttl_seconds=10800)
        return session
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/sessions/{session_id}/consent")
def save_consent(session_id: str) -> dict[str, object]:
    session = require_session(session_id)
    updated = store.update_session(session_id, {"consent_given": True, "consent_given_at": store.appeal_deadline(), "status": "consented"})
    normalized = store.normalize_session(updated)
    redis_hot_state.set_json(f"session:{session_id}:state", normalized, ttl_seconds=10800)
    redis_hot_state.push_event(f"exam:{normalized['exam_id']}:events", {"type": "consent_given", "session_id": session_id}, ttl_seconds=10800)
    return normalized


@app.post("/api/v1/sessions/{session_id}/liveness")
def save_liveness(session_id: str) -> dict[str, object]:
    session = require_session(session_id)
    if not _get_session_field(session, "consent"):
        raise HTTPException(status_code=422, detail="consent is required before liveness")
    updated = store.update_session(session_id, {"liveness_verified": True, "status": "active", "started_at": store.appeal_deadline()})
    normalized = store.normalize_session(updated)
    redis_hot_state.set_json(f"session:{session_id}:state", normalized, ttl_seconds=10800)
    redis_hot_state.push_event(f"exam:{normalized['exam_id']}:events", {"type": "liveness_verified", "session_id": session_id}, ttl_seconds=10800)
    return normalized


@app.get("/api/v1/sessions/{session_id}/questions")
def session_questions(session_id: str) -> list[dict[str, object]]:
    session = require_session(session_id)
    if not _get_session_field(session, "liveness"):
        raise HTTPException(status_code=422, detail="liveness is required before questions")
    return store.session_questions(session_id)


@app.post("/api/v1/sessions/{session_id}/answers")
@limiter.limit("60/minute")
def save_answer(request: Request, session_id: str, payload: AnswerRequest) -> dict[str, object]:
    session = require_session(session_id)
    if not payload.answer_text and not payload.selected_option:
        raise HTTPException(status_code=422, detail="answer text or selected option is required")
    answer = store.save_answer(session_id, payload.model_dump())
    redis_hot_state.push_event(f"exam:{session['exam_id']}:events", {"type": "answer_saved", "session_id": session_id, "question_id": payload.question_id}, ttl_seconds=10800)
    return answer


@app.post("/api/v1/sessions/{session_id}/end")
def end_session(session_id: str) -> dict[str, object]:
    session = require_session(session_id)
    updated = store.update_session(session_id, {"status": "ended", "ended_at": store.appeal_deadline()})
    return store.normalize_session(updated)


@app.get("/api/v1/sessions/{session_id}/integrity")
def session_integrity(session_id: str) -> dict[str, object]:
    return require_session(session_id)["integrity"]


@app.get("/api/v1/sessions/{session_id}/result")
def session_result(session_id: str) -> dict[str, object]:
    """Get session result with answers, integrity, and review status."""
    try:
        return store.get_session_result(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@app.post("/api/v1/sessions/{session_id}/appeal")
def submit_appeal(session_id: str, payload: AppealRequest) -> dict[str, object]:
    try:
        return store.submit_appeal(session_id, payload.response)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@app.put("/api/v1/sessions/{session_id}/decision")
def teacher_decision(session_id: str, payload: DecisionRequest) -> dict[str, object]:
    try:
        return store.teacher_decision(session_id, payload.decision, payload.teacher_note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


# --- Proctoring Events -------------------------------------------------------


@app.post("/api/v1/sessions/{session_id}/events")
def log_proctoring_event(session_id: str, payload: ProctoringEventRequest) -> dict[str, str]:
    """Log a browser-side proctoring event (tab switch, paste, gaze, etc.)."""
    session = require_session(session_id)
    event = {"type": payload.event_type, **payload.metadata, "session_id": session_id}
    redis_hot_state.push_event(f"exam:{session['exam_id']}:events", event, ttl_seconds=10800)
    return {"status": "logged"}


# --- Settings ----------------------------------------------------------------


@app.put("/api/v1/users/{user_id}/settings")
def save_settings(user_id: str, payload: SettingsRequest) -> dict[str, object]:
    """Save user settings (display name, institute, notifications)."""
    try:
        return store.save_settings(user_id, payload.display_name, payload.institute_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc


# --- Reports -----------------------------------------------------------------


@app.post("/api/v1/sessions/{session_id}/reports/generate")
def generate_session_report(session_id: str) -> dict[str, str]:
    session = require_session(session_id)
    store.generate_report_pdf(session_id)
    redis_hot_state.push_event(f"exam:{session['exam_id']}:events", {"type": "report_ready", "session_id": session_id}, ttl_seconds=10800)
    return {"status": "ready", "download_url": f"/api/v1/sessions/{session_id}/reports/pdf"}


@app.get("/api/v1/sessions/{session_id}/reports/pdf")
def report_pdf(session_id: str) -> Response:
    require_session(session_id)
    data = store.reports.get(session_id) or store.generate_report_pdf(session_id)
    return Response(content=data, media_type="application/pdf")


# --- Internal ----------------------------------------------------------------


def require_session(session_id: str) -> dict[str, object]:
    try:
        raw = store.require_session(session_id)
        return store.normalize_session(raw)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
