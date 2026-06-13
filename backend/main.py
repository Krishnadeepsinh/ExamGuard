"""ExamGuard AI v6 FastAPI application.

Uses Supabase in production and an isolated in-memory store for local tests.
"""

from __future__ import annotations

import csv
import asyncio
import base64
import hashlib
import hmac
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.agents.constants import FACTOR_WEIGHTS
from backend.agents.graph import AGENT_NODES, EDGES, run_workflow
from backend.config import settings
from backend.redis_client import redis_hot_state
from backend.store import build_class_pdf_report, store as local_store

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
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=settings.cors_origin_regex or None,
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


class DemoLoginRequest(BaseModel):
    email: str
    password: str


class StudentAccessRequest(BaseModel):
    student_name: str = Field(min_length=3, max_length=80)
    email: str | None = None
    device_id: str | None = Field(default=None, min_length=8, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_student_email(cls, value: str | None) -> str | None:
        if value and ("@" not in value or "." not in value.rsplit("@", 1)[-1]):
            raise ValueError("valid email is required")
        return value.strip().lower() if value else None


class ExamCreateRequest(BaseModel):
    teacher_id: str
    title: str = Field(min_length=3, max_length=120)
    subject: str = Field(min_length=2, max_length=80)
    duration_minutes: int = Field(ge=10, le=300)
    total_marks: int = Field(ge=10, le=300)


class ExamScheduleRequest(BaseModel):
    scheduled_start_at: datetime


class SectionConfig(BaseModel):
    id: str
    type: Literal["MCQ", "Short Answer", "Long Answer", "Fill Blank", "True/False", "Essay"]
    count: int = Field(ge=1, le=100)
    marks_each: int = Field(ge=1, le=20)
    bloom: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    chapter_tag: str = Field(min_length=2)
    topic_tag: Optional[str] = "All topics"
    level: Literal["Use overall", "Easy", "Standard", "Challenging"] = "Use overall"


class PaperConfigRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: list[str] = Field(default_factory=list)
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
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class AppealRequest(BaseModel):
    response: str = Field(min_length=40, max_length=3500)


class DecisionRequest(BaseModel):
    decision: Literal["clear", "confirm_flag"]
    teacher_note: str = Field(min_length=12, max_length=1200)


class ProctoringEventRequest(BaseModel):
    event_type: str
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        allowed = {
            "tab_switch", "tab_hidden", "window_blur", "fullscreen_exit",
            "gaze_away", "paste_detected", "right_click", "phone_detected",
            "audio_spike", "face_missing", "multiple_faces", "monitoring_interrupted",
        }
        if value not in allowed:
            raise ValueError("unsupported proctoring event type")
        return value


class LivenessRequest(BaseModel):
    method: Literal["mediapipe_ear"]
    blink_count: int = Field(ge=2, le=10)
    duration_ms: int = Field(ge=250, le=15000)
    threshold: float = Field(ge=0.15, le=0.35)


class SettingsRequest(BaseModel):
    display_name: str = Field(min_length=3, max_length=80)
    institute_name: str = Field(min_length=2, max_length=120)
    email_on_flag: bool = True


# --- Helper ------------------------------------------------------------------


def _get_session_field(session: dict, field: str) -> object:
    """Safely get session fields that may differ between local/supabase stores."""
    if field == "consent":
        return session.get("consent", session.get("consent_given", False))
    if field == "liveness":
        return session.get("liveness", session.get("liveness_verified", False))
    return session.get(field)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_expired(session: dict[str, object], exam: dict[str, object]) -> bool:
    expiry = session.get("expires_at")
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(str(expiry).replace("Z", "+00:00")) <= datetime.now(timezone.utc)
    except ValueError:
        return False


def issue_demo_token(user: dict[str, object]) -> str:
    expires = int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp())
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user["id"], "email": user["email"], "exp": expires}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(demo_signing_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"demo.{payload}.{signature}"


def issue_student_token(student_id: str, email: str) -> str:
    expires = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    payload = base64.urlsafe_b64encode(json.dumps({"sub": student_id, "email": email, "role": "student", "exp": expires}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(demo_signing_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"student.{payload}.{signature}"


def verify_student_token(token: str) -> dict[str, object] | None:
    if not token.startswith("student."):
        return None
    try:
        _, payload, signature = token.split(".", 2)
        expected = hmac.new(demo_signing_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if decoded.get("role") != "student" or int(decoded["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            return None
        return {"id": decoded["sub"], "email": decoded["email"], "role": "student"}
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def verify_demo_token(token: str) -> dict[str, object] | None:
    if not settings.demo_access_enabled or not token.startswith("demo."):
        return None
    try:
        _, payload, signature = token.split(".", 2)
        expected = hmac.new(demo_signing_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(decoded["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            return None
        user = store.ensure_demo_teacher(str(decoded["email"]))
        return user if str(user.get("id")) == str(decoded["sub"]) else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def demo_signing_secret() -> bytes:
    configured = settings.demo_session_secret or settings.supabase_service_role_key
    if not configured:
        configured = "examguard-local-demo-signing-key"
    return hashlib.sha256(f"examguard-demo:{configured}".encode()).digest()


def current_teacher(authorization: str | None = Header(default=None)) -> dict[str, object]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Teacher authentication is required")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        user = verify_demo_token(token) or store.verify_token(token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher role is required")
    return user


def current_user(authorization: str | None = Header(default=None)) -> dict[str, object]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication is required")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        user = verify_student_token(token) or verify_demo_token(token) or store.verify_token(token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return user


def current_student(user: dict[str, object] = Depends(current_user)) -> dict[str, object]:
    if user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student role is required")
    return user


def require_student_session(session_id: str, student: dict[str, object]) -> dict[str, object]:
    session = require_session(session_id)
    if str(session.get("student_id")) != str(student.get("id")):
        raise HTTPException(status_code=403, detail="This exam attempt belongs to another student")
    return session


def require_owned_exam(exam_id: str, teacher: dict[str, object]) -> dict[str, object]:
    exam = lookup_exam(exam_id)
    if exam.get("teacher_id") != teacher.get("id"):
        raise HTTPException(status_code=403, detail="You do not own this exam")
    return exam


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
        "langgraph": "active",
    }


@app.get("/api/v1/agents/graph")
def agent_graph() -> dict[str, object]:
    trace = run_workflow("answer", {"proof": True})
    return {"nodes": AGENT_NODES, "edges": EDGES, "sample_trace": trace.get("completed_agents", [])}


# --- Auth --------------------------------------------------------------------


@app.post("/api/v1/auth/demo")
@limiter.limit("10/minute")
def demo_login(request: Request, payload: DemoLoginRequest) -> dict[str, object]:
    if not settings.demo_access_enabled or not settings.demo_teacher_password:
        raise HTTPException(status_code=404, detail="Demo access is not configured")
    valid_email = hmac.compare_digest(payload.email.strip().lower(), settings.demo_teacher_email)
    valid_password = hmac.compare_digest(payload.password, settings.demo_teacher_password)
    if not valid_email or not valid_password:
        raise HTTPException(status_code=401, detail="Invalid demo credentials")
    user = store.ensure_demo_teacher(settings.demo_teacher_email)
    return {"user": user, "token": issue_demo_token(user), "demo": True}


@app.post("/api/v1/auth/login")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest) -> dict[str, object]:
    try:
        user = store.login(payload.email, payload.password, payload.role, payload.display_name, signup=False)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    token = user.pop("access_token", f"local-{user['id']}")
    user.pop("refresh_token", None)
    user.pop("password", None)
    return {"user": user, "token": token}


@app.post("/api/v1/auth/student-access")
@limiter.limit("10/minute")
def student_access(request: Request, payload: StudentAccessRequest) -> dict[str, object]:
    if not payload.email and not payload.device_id:
        raise HTTPException(status_code=422, detail="email or device_id is required")
    identity_email = payload.email or f"guest-{hashlib.sha256(f'{payload.device_id}:{payload.student_name.strip().lower()}'.encode()).hexdigest()[:24]}@student.local"
    user = store.ensure_student(identity_email, payload.student_name.strip())
    return {"user": user, "token": issue_student_token(str(user["id"]), str(user["email"]))}


@app.post("/api/v1/auth/signup")
@limiter.limit("5/minute")
def signup(request: Request, payload: LoginRequest) -> dict[str, object]:
    try:
        user = store.login(payload.email, payload.password, payload.role, payload.display_name, signup=True)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = user.pop("access_token", f"local-{user['id']}")
    user.pop("refresh_token", None)
    user.pop("password", None)
    return {"user": user, "token": token}


@app.post("/api/v1/auth/reset-request")
@limiter.limit("3/minute")
def reset_request(request: Request, payload: dict[str, str]) -> dict[str, str]:
    email = payload.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    try:
        store.request_password_reset(email)
    except PermissionError:
        # Do not reveal whether an account exists.
        pass
    return {"status": "reset_link_sent"}


@app.post("/api/v1/auth/reset-confirm")
@limiter.limit("3/minute")
def reset_confirm(request: Request, payload: dict[str, str]) -> dict[str, str]:
    password = payload.get("password", "")
    token = payload.get("token", "").strip()
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    if not token:
        raise HTTPException(status_code=422, detail="reset token is required")
    try:
        store.confirm_password_reset(token, password)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"status": "password_updated"}


# --- Exams -------------------------------------------------------------------


@app.post("/api/v1/exams")
@limiter.limit("20/minute")
def create_exam(request: Request, payload: ExamCreateRequest, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    if payload.teacher_id != teacher["id"]:
        raise HTTPException(status_code=403, detail="teacher_id must match authenticated user")
    if hasattr(store, "users") and payload.teacher_id not in store.users:
        raise HTTPException(status_code=404, detail="teacher not found")
    return store.create_exam(payload.teacher_id, payload.model_dump())


@app.get("/api/v1/exams")
def list_exams(teacher_id: str | None = None, teacher: dict[str, object] = Depends(current_teacher)) -> list[dict[str, object]]:
    teacher_id = str(teacher["id"])
    if hasattr(store, "list_exams"):
        return store.list_exams(teacher_id)
    exams = list(store.exams.values())
    if teacher_id:
        exams = [exam for exam in exams if exam["teacher_id"] == teacher_id]
    return exams


@app.get("/api/v1/exams/{exam_id}")
def get_exam_route(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    return require_owned_exam(exam_id, teacher)


def lookup_exam(exam_id: str) -> dict[str, object]:
    if hasattr(store, "get_exam"):
        try:
            return store.get_exam(exam_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="exam not found") from exc
    if exam_id not in store.exams:
        raise HTTPException(status_code=404, detail="exam not found")
    return store.exams[exam_id]


@app.delete("/api/v1/exams/{exam_id}")
def delete_exam(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, str]:
    """Delete an exam and all associated data."""
    require_owned_exam(exam_id, teacher)
    try:
        store.delete_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    return {"status": "deleted"}


@app.post("/api/v1/exams/{exam_id}/clone")
def clone_exam(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    """Clone an exam with a new join code."""
    require_owned_exam(exam_id, teacher)
    try:
        return store.clone_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc


@app.put("/api/v1/exams/{exam_id}/paper-config")
def save_paper_config(exam_id: str, payload: PaperConfigRequest, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    require_owned_exam(exam_id, teacher)
    if payload.material_id:
        try:
            material = store.get_material(payload.material_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="material not found") from exc
        if str(material.get("exam_id")) != exam_id:
            raise HTTPException(status_code=422, detail="selected material does not belong to this exam")
    try:
        result = store.configure_exam(exam_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result["status"] == "invalid":
        raise HTTPException(status_code=422, detail=result["errors"])
    return result


@app.post("/api/v1/exams/{exam_id}/generate")
@limiter.limit("5/minute")
def generate_paper(request: Request, exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    exam = require_owned_exam(exam_id, teacher)
    if not exam.get("paper_config"):
        raise HTTPException(status_code=422, detail="paper config must be saved before generation")
    try:
        result = store.generate_questions(exam_id)
        result["agent_trace"] = run_workflow("generate", {"exam_id": exam_id, "question_count": result.get("count", 0)}).get("completed_agents", [])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/exams/{exam_id}/questions")
def teacher_exam_questions(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> list[dict[str, object]]:
    require_owned_exam(exam_id, teacher)
    try:
        return store.exam_questions(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc


@app.post("/api/v1/exams/{exam_id}/activate")
def activate_exam(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    require_owned_exam(exam_id, teacher)
    try:
        return store.activate_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/exams/{exam_id}/schedule")
def schedule_exam(exam_id: str, payload: ExamScheduleRequest, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    require_owned_exam(exam_id, teacher)
    if payload.scheduled_start_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Scheduled start must be in the future")
    try:
        return store.schedule_exam(exam_id, payload.scheduled_start_at.isoformat())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/exams/{exam_id}/pause")
def pause_exam(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    """Pause an active exam — freezes all student timers."""
    require_owned_exam(exam_id, teacher)
    try:
        return store.pause_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/exams/{exam_id}/resume")
def resume_exam(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    """Resume a paused exam."""
    require_owned_exam(exam_id, teacher)
    try:
        return store.resume_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/exams/{exam_id}/end")
def end_exam(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    require_owned_exam(exam_id, teacher)
    try:
        return store.end_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="exam not found") from exc


@app.get("/api/v1/exams/{exam_id}/students")
def exam_students(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> list[dict[str, object]]:
    require_owned_exam(exam_id, teacher)
    if hasattr(store, "exam_students"):
        return store.exam_students(exam_id)
    return [session for session in store.sessions.values() if session["exam_id"] == exam_id]


@app.post("/api/v1/exams/{exam_id}/results/release")
def release_exam_results(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, int]:
    require_owned_exam(exam_id, teacher)
    return store.release_exam_results(exam_id)


@app.get("/api/v1/exams/{exam_id}/materials")
def exam_materials(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> list[dict[str, object]]:
    require_owned_exam(exam_id, teacher)
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


def owned_exam_sessions(exam_id: str, teacher: dict[str, object]) -> list[dict[str, object]]:
    require_owned_exam(exam_id, teacher)
    if hasattr(store, "exam_students"):
        return store.exam_students(exam_id)
    return [session for session in store.sessions.values() if session["exam_id"] == exam_id]


@app.get("/api/v1/exams/{exam_id}/reports")
def exam_reports(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    sessions = owned_exam_sessions(exam_id, teacher)
    return {
        "exam_id": exam_id,
        "reports_ready": len(sessions),
        "students": sessions,
        "average_integrity": round(sum(s["integrity"]["score"] for s in sessions) / len(sessions), 2) if sessions else 0,
    }


@app.get("/api/v1/exams/{exam_id}/reports/csv")
def exam_reports_csv(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> StreamingResponse:
    """Export exam reports as CSV download."""
    sessions = owned_exam_sessions(exam_id, teacher)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_name", "student_id", "marks_earned", "total_marks", "percentage", "integrity_score", "integrity_status", "cheat_review", "result_released"])
    for s in sessions:
        integrity = s.get("integrity", {})
        grade = s.get("grade", {}) or {}
        writer.writerow([
            s.get("student_name", ""),
            s.get("student_id", ""),
            grade.get("earned_marks", ""),
            grade.get("total_marks", ""),
            grade.get("percentage", ""),
            integrity.get("score", ""),
            integrity.get("status", ""),
            s.get("review_status", ""),
            s.get("grade_released", False),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=examguard_{exam_id}_report.csv"},
    )


@app.get("/api/v1/exams/{exam_id}/reports/pdf")
def exam_reports_pdf(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> Response:
    """Generate a paginated class report with an overview and student detail pages."""
    exam = require_owned_exam(exam_id, teacher)
    sessions = owned_exam_sessions(exam_id, teacher)
    data = build_class_pdf_report(exam, sessions)
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=examguard_{exam_id}_class_report.pdf"})


@app.get("/api/v1/exams/{exam_id}/reports/summary")
def exam_summary(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    """Summary statistics for an exam."""
    sessions = owned_exam_sessions(exam_id, teacher)
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
def live_events(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    require_owned_exam(exam_id, teacher)
    return {
        "exam_id": exam_id,
        "redis": "upstash" if settings.redis_enabled else "disabled",
        "events": redis_hot_state.list_events(f"exam:{exam_id}:events") if settings.redis_enabled else [],
    }


@app.get("/api/v1/exams/{exam_id}/live")
def live_snapshot(exam_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    """Return full monitor snapshot for reconnects and non-WebSocket clients."""
    require_owned_exam(exam_id, teacher)
    sessions = store.exam_students(exam_id) if hasattr(store, "exam_students") else [
        session for session in store.sessions.values() if session["exam_id"] == exam_id
    ]
    return {
        "exam_id": exam_id,
        "students": sessions,
        "events": redis_hot_state.list_events(f"exam:{exam_id}:events") if settings.redis_enabled else [],
    }


@app.websocket("/api/v1/ws/exams/{exam_id}")
async def exam_live_socket(websocket: WebSocket, exam_id: str, token: str = "") -> None:
    """Push authoritative monitor snapshots; Redis keeps events across workers."""
    try:
        teacher = verify_demo_token(token) or store.verify_token(token)
        require_owned_exam(exam_id, teacher)
    except (PermissionError, HTTPException):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    last_payload = ""
    try:
        while True:
            students = store.exam_students(exam_id)
            events = redis_hot_state.list_events(f"exam:{exam_id}:events") if settings.redis_enabled else []
            payload = {"type": "monitor_snapshot", "exam_id": exam_id, "students": students, "events": events[:50]}
            encoded = json.dumps(payload, sort_keys=True, default=str)
            if encoded != last_payload:
                await websocket.send_json(payload)
                last_payload = encoded
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


# --- Materials ---------------------------------------------------------------


@app.post("/api/v1/materials/upload")
@limiter.limit("10/minute")
async def upload_material(request: Request, exam_id: str, source_type: Literal["syllabus", "material"] = "material", file: UploadFile = File(...), teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    require_owned_exam(exam_id, teacher)
    if not file.filename:
        raise HTTPException(status_code=422, detail="filename is required")
    if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=422, detail="only PDF, DOCX, or TXT files are allowed")
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="material file must be 50MB or smaller")
    try:
        material = store.add_material(exam_id, file.filename, content, source_type)
        run_workflow("ingest", {"exam_id": exam_id, "material_id": material["id"]})
        return material
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/materials/{material_id}/status")
def material_status(material_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    try:
        material = store.get_material(material_id)
        require_owned_exam(str(material["exam_id"]), teacher)
        return {key: value for key, value in material.items() if key != "chunks"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="material not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete("/api/v1/materials/{material_id}")
def delete_material(material_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, str]:
    """Delete uploaded material."""
    try:
        material = store.get_material(material_id)
        require_owned_exam(str(material["exam_id"]), teacher)
        store.delete_material(material_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="material not found") from exc
    return {"status": "deleted"}


# --- Sessions ----------------------------------------------------------------


@app.post("/api/v1/sessions/join")
@limiter.limit("15/minute")
def join_session(request: Request, payload: JoinRequest, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    try:
        session = store.join_session(payload.join_code.upper(), payload.student_name, str(student.get("email") or payload.email or ""), str(student["id"]))
        redis_hot_state.set_json(f"session:{session['id']}:state", session, ttl_seconds=10800)
        redis_hot_state.push_event(f"exam:{session['exam_id']}:events", {"type": "student_joined", "session_id": session["id"], "student_name": session["student_name"]}, ttl_seconds=10800)
        session["student_access_token"] = issue_student_token(str(session["student_id"]), str(student.get("email") or ""))
        return session
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0] if exc.args else "Invalid join code") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/students/me/sessions")
def student_sessions(user: dict[str, object] = Depends(current_user)) -> list[dict[str, object]]:
    if user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student role is required")
    return store.student_sessions(str(user["id"]))


@app.post("/api/v1/sessions/{session_id}/consent")
def save_consent(session_id: str, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    session = require_student_session(session_id, student)
    if session.get("status") == "ended":
        raise HTTPException(status_code=409, detail="You already submitted this exam.")
    updated = store.update_session(session_id, {"consent_given": True, "consent_given_at": store.appeal_deadline(), "status": "consented"})
    normalized = store.normalize_session(updated)
    redis_hot_state.set_json(f"session:{session_id}:state", normalized, ttl_seconds=10800)
    redis_hot_state.push_event(f"exam:{normalized['exam_id']}:events", {"type": "consent_given", "session_id": session_id}, ttl_seconds=10800)
    return normalized


@app.post("/api/v1/sessions/{session_id}/liveness")
def save_liveness(session_id: str, payload: LivenessRequest, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    session = require_student_session(session_id, student)
    if session.get("status") == "ended":
        raise HTTPException(status_code=409, detail="You already submitted this exam.")
    if not _get_session_field(session, "consent"):
        raise HTTPException(status_code=422, detail="consent is required before liveness")
    exam = lookup_exam(str(session["exam_id"]))
    started_at = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=int(exam["duration_minutes"]))).isoformat()
    updated = store.update_session(session_id, {
        "liveness_verified": True, "status": "active", "started_at": started_at, "expires_at": expires_at,
    })
    normalized = store.normalize_session(updated)
    redis_hot_state.set_json(f"session:{session_id}:state", normalized, ttl_seconds=10800)
    redis_hot_state.push_event(f"exam:{normalized['exam_id']}:events", {"type": "liveness_verified", "session_id": session_id}, ttl_seconds=10800)
    if hasattr(store, "log_integrity_event"):
        store.log_integrity_event(session_id, "liveness_verified", payload.model_dump())
    return normalized


def student_safe_question(question: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in question.items() if key not in {"correct_answer", "source_chunk_ids"}}


@app.get("/api/v1/sessions/{session_id}/questions")
def session_questions(session_id: str, student: dict[str, object] = Depends(current_student)) -> list[dict[str, object]]:
    session = require_student_session(session_id, student)
    if session.get("status") == "ended":
        raise HTTPException(status_code=409, detail="You already submitted this exam.")
    if not _get_session_field(session, "liveness"):
        raise HTTPException(status_code=422, detail="liveness is required before questions")
    return [student_safe_question(question) for question in store.session_questions(session_id)]


@app.get("/api/v1/sessions/{session_id}/exam")
def session_exam(session_id: str, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    session = require_student_session(session_id, student)
    exam = lookup_exam(str(session["exam_id"]))
    result = {key: exam.get(key) for key in ("id", "title", "subject", "duration_minutes", "total_marks", "status")}
    result["expires_at"] = session.get("expires_at")
    result["session_status"] = session.get("status")
    expiry = session.get("expires_at")
    if expiry:
        try:
            deadline = datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
            result["remaining_seconds"] = max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))
        except ValueError:
            result["remaining_seconds"] = None
    else:
        result["remaining_seconds"] = None
    result["server_now"] = now_iso()
    return result


@app.post("/api/v1/sessions/{session_id}/answers")
@limiter.limit("60/minute")
def save_answer(request: Request, session_id: str, payload: AnswerRequest, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    session = require_student_session(session_id, student)
    if not _get_session_field(session, "consent") or not _get_session_field(session, "liveness"):
        raise HTTPException(status_code=403, detail="consent and liveness are required before answering")
    if session.get("status") != "active":
        raise HTTPException(status_code=409, detail="session is not active")
    if session.get("locked_for_review"):
        raise HTTPException(status_code=423, detail="This attempt is paused after repeated independent integrity signals. Saved answers are preserved for teacher review.")
    exam = lookup_exam(str(session["exam_id"]))
    if session_expired(session, exam):
        store.update_session(session_id, {"status": "ended", "ended_at": now_iso()})
        raise HTTPException(status_code=409, detail="exam time has expired; answers are no longer accepted")
    if not payload.answer_text and not payload.selected_option:
        raise HTTPException(status_code=422, detail="answer text or selected option is required")
    answer = store.save_answer(session_id, payload.model_dump())
    run_workflow("answer", {"session_id": session_id, "question_id": payload.question_id})
    redis_hot_state.push_event(f"exam:{session['exam_id']}:events", {"type": "answer_saved", "session_id": session_id, "question_id": payload.question_id}, ttl_seconds=10800)
    return answer


@app.post("/api/v1/sessions/{session_id}/end")
def end_session(session_id: str, reason: str = "manual", student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    session = require_student_session(session_id, student)
    if session.get("status") == "ended":
        return store.normalize_session(session)
    exam = lookup_exam(str(session["exam_id"]))
    if reason == "expired" and not session_expired(session, exam):
        raise HTTPException(status_code=409, detail="The exam timer has not expired. Your attempt remains active.")
    if reason not in {"manual", "expired", "teacher_ended"}:
        raise HTTPException(status_code=422, detail="Invalid submission reason")
    if hasattr(store, "evaluate_session"):
        store.evaluate_session(session_id)
    run_workflow("finish", {"session_id": session_id})
    updated = store.update_session(session_id, {"status": "ended", "ended_at": now_iso()})
    return store.normalize_session(updated)


@app.get("/api/v1/sessions/{session_id}/integrity")
def session_integrity(session_id: str, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    raw_session = require_student_session(session_id, student)
    session = store.normalize_session(raw_session)
    integrity = dict(session.get("integrity") or {})
    integrity["locked_for_review"] = bool(session.get("locked_for_review", False))
    integrity["warning_count"] = store.session_warning_count(session_id) if hasattr(store, "session_warning_count") else 0
    integrity["event_summary"] = store.session_event_summary(session_id) if hasattr(store, "session_event_summary") else {}
    return integrity


@app.get("/api/v1/sessions/{session_id}/result")
def session_result(session_id: str, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    """Get session result with answers, integrity, and review status."""
    try:
        require_student_session(session_id, student)
        return store.get_session_result(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@app.post("/api/v1/sessions/{session_id}/appeal")
def submit_appeal(session_id: str, payload: AppealRequest, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    try:
        require_student_session(session_id, student)
        return store.submit_appeal(session_id, payload.response)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@app.put("/api/v1/sessions/{session_id}/decision")
def teacher_decision(session_id: str, payload: DecisionRequest, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    session = require_session(session_id)
    require_owned_exam(str(session["exam_id"]), teacher)
    try:
        return store.teacher_decision(session_id, payload.decision, payload.teacher_note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


# --- Proctoring Events -------------------------------------------------------


@app.post("/api/v1/sessions/{session_id}/events")
def log_proctoring_event(session_id: str, payload: ProctoringEventRequest, student: dict[str, object] = Depends(current_student)) -> dict[str, object]:
    """Log a browser-side proctoring event (tab switch, paste, gaze, etc.)."""
    session = require_student_session(session_id, student)
    if session.get("status") != "active":
        raise HTTPException(status_code=409, detail="proctoring events are accepted only during an active session")
    event = {"type": payload.event_type, **payload.metadata, "session_id": session_id}
    updated_integrity = None
    if hasattr(store, "log_integrity_event"):
        stored_event = store.log_integrity_event(session_id, payload.event_type, payload.metadata)
        updated_integrity = stored_event.get("integrity")
        if updated_integrity:
            event["integrity"] = updated_integrity
        event["warning_count"] = stored_event.get("warning_count", 0)
        event["locked_for_review"] = stored_event.get("locked_for_review", False)
    redis_hot_state.push_event(f"exam:{session['exam_id']}:events", event, ttl_seconds=10800)
    run_workflow("proctor", event, str(session.get("integrity", {}).get("status", "CLEAN")))
    return {"status": "logged", "integrity": updated_integrity, "warning_count": event.get("warning_count", 0), "locked_for_review": event.get("locked_for_review", False)}


# --- Settings ----------------------------------------------------------------


@app.put("/api/v1/users/{user_id}/settings")
def save_settings(user_id: str, payload: SettingsRequest, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, object]:
    """Save user settings (display name, institute, notifications)."""
    if user_id != teacher["id"]:
        raise HTTPException(status_code=403, detail="You can update only your own settings")
    try:
        return store.save_settings(user_id, payload.display_name, payload.institute_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc


# --- Reports -----------------------------------------------------------------


@app.post("/api/v1/sessions/{session_id}/reports/generate")
def generate_session_report(session_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> dict[str, str]:
    session = require_session(session_id)
    require_owned_exam(str(session["exam_id"]), teacher)
    store.generate_report_pdf(session_id)
    redis_hot_state.push_event(f"exam:{session['exam_id']}:events", {"type": "report_ready", "session_id": session_id}, ttl_seconds=10800)
    return {"status": "ready", "download_url": f"/api/v1/sessions/{session_id}/reports/pdf"}


@app.get("/api/v1/sessions/{session_id}/reports/pdf")
def report_pdf(session_id: str, teacher: dict[str, object] = Depends(current_teacher)) -> Response:
    session = require_session(session_id)
    require_owned_exam(str(session["exam_id"]), teacher)
    data = store.reports.get(session_id) or store.generate_report_pdf(session_id)
    return Response(content=data, media_type="application/pdf")


# --- Internal ----------------------------------------------------------------


def require_session(session_id: str) -> dict[str, object]:
    try:
        raw = store.require_session(session_id)
        return store.normalize_session(raw)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
