"""Comprehensive verification and integration test for the ExamGuard AI v6 platform.

This script executes the entire lifecycle of a teacher configuring an exam,
uploading syllabus, generating questions, and a student joining, consenting,
passing liveness, answering questions, generating reports, submitting appeals,
and the teacher making a final decision.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import urllib.parse
import sys
import os
from uuid import uuid4

BASE_URL = os.getenv("EXAMGUARD_BASE_URL", "http://127.0.0.1:8000/api/v1")

AUTH_TOKEN = ""

def call(method: str, path: str, payload: dict | None = None, is_multipart: bool = False, raw_data: bytes | None = None, content_type: str | None = None, expected_status: int | None = None) -> dict | list | bytes:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}
    
    if is_multipart and content_type:
        headers["Content-Type"] = content_type
        data = raw_data
    elif payload is not None:
        headers["Content-Type"] = application_json = "application/json"
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None
        
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        timeout = 120 if "/materials/upload" in path or path.endswith("/generate") else 30
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_content = response.read()
            if path.endswith("/pdf"):
                return res_content
            decoded = res_content.decode("utf-8")
            return json.loads(decoded) if decoded else {}
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="ignore")
        if expected_status == exc.code:
            return json.loads(err_msg) if err_msg else {"status": exc.code}
        print(f"Error calling {method} {path}: {exc.code} - {err_msg}")
        raise RuntimeError(f"HTTP {exc.code}: {err_msg}") from exc

def encode_multipart_formdata(fields: dict[str, str], files: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    lines = []
    for name, value in fields.items():
        lines.extend([
            f"--{boundary}".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"),
            "".encode("utf-8"),
            str(value).encode("utf-8")
        ])
    for name, (filename, content) in files.items():
        lines.extend([
            f"--{boundary}".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode("utf-8"),
            "Content-Type: text/plain".encode("utf-8"),
            "".encode("utf-8"),
            content
        ])
    lines.append(f"--{boundary}--".encode("utf-8"))
    
    # Use b"\r\n".join for binary safety
    body = b"\r\n".join(lines) + b"\r\n"
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type

def run_test() -> None:
    global AUTH_TOKEN
    print("======================================================================")
    print("        EXAMGUARD AI V6 INTEGRATION & VERIFICATION TEST SUITE         ")
    print("======================================================================\n")

    # Step 1: Teacher Auth
    print("[1/15] Authenticating an isolated Teacher account...")
    run_id = uuid4().hex[:8]
    demo_email = os.getenv("DEMO_TEACHER_EMAIL", "").strip()
    demo_password = os.getenv("DEMO_TEACHER_PASSWORD", "").strip()
    if demo_email and demo_password:
        teacher_login = call("POST", "/auth/demo", {"email": demo_email, "password": demo_password})
    else:
        teacher_email = f"teacher-{run_id}@example.com"
        teacher_login = call("POST", "/auth/signup", {
            "email": teacher_email,
            "password": "ExamGuard-Test-2026!",
            "role": "teacher",
            "display_name": "Rajan Kumar",
        })
    teacher_id = teacher_login["user"]["id"]
    teacher_token = teacher_login["token"]
    AUTH_TOKEN = teacher_token
    print(f"  -> Success! Logged in as: {teacher_login['user']['display_name']} (ID: {teacher_id})")

    # Step 2: Create new Exam Shell
    print("\n[2/15] Creating a new Physics Exam...")
    exam = call("POST", "/exams", {
        "teacher_id": teacher_id,
        "title": "SQL Source-Locked Audit Exam",
        "subject": "SQL",
        "duration_minutes": 120,
        "total_marks": 10
    })
    exam_id = exam["id"]
    join_code = exam["join_code"]
    print(f"  -> Success! Exam Created (ID: {exam_id}, Join Code: {join_code})")

    # Step 3: Upload Syllabus Material to this Exam
    print("\n[3/15] Uploading syllabus textbook file to the exam...")
    file_content = (
        "Chapter 12 Electromagnetic Induction explains magnetic flux, induced EMF, Faraday law, "
        "Lenz law, self induction, mutual induction, generators, and transformers. "
        "Chapter 13 Alternating Current explains AC voltage applied to resistor, inductor, capacitor, "
        "LCR series circuit, resonance, power in AC circuit, LC oscillations, and transformers. "
        "Chapter 14 Electromagnetic Waves explains displacement current, electromagnetic waves, "
        "electromagnetic spectrum, and propagation of waves."
    ) * 80  # Multiply to meet chunk limits
    
    raw_body, content_type = encode_multipart_formdata(
        {},
        {"file": ("NCERT_Electromagnetism_Syllabus.txt", file_content.encode("utf-8"))}
    )
    
    material = call(
        "POST", 
        f"/materials/upload?exam_id={exam_id}", 
        is_multipart=True, 
        raw_data=raw_body, 
        content_type=content_type
    )
    material_id = material["id"]
    chapter_tag = next(iter(material["chapter_counts"]))
    print(f"  -> Success! Material Uploaded (ID: {material_id}, File: {material['filename']}, Chunks: {material['chunk_count']})")

    # Step 4: Save Paper Configuration
    print("\n[4/15] Saving paper layout configuration...")
    config_payload = {
        "material_id": material_id,
        "total_marks": 10,
        "overall_level": "Standard",
        "paper_mode": "Mixed",
        "sections": [
            {
                "id": "A",
                "type": "MCQ",
                "count": 5,
                "marks_each": 2,
                "bloom": "Remember",
                "chapter_tag": chapter_tag,
                "level": "Use overall"
            }
        ]
    }
    config_res = call("PUT", f"/exams/{exam_id}/paper-config", config_payload)
    print(f"  -> Success! Configuration saved (Status: {config_res['status']})")

    # Step 5: Generate Grounded Questions
    print("\n[5/15] Generating source-locked questions using materials chunks...")
    questions_res = call("POST", f"/exams/{exam_id}/generate")
    questions = questions_res["questions"]
    print(f"  -> Success! Generated {questions_res['count']} questions.")
    print(f"     Example generated question: \"{questions[0]['text']}\" (Marks: {questions[0]['marks']})")

    # Step 6: Activate Exam for Students to Join
    print("\n[6/15] Activating the exam...")
    activated_exam = call("POST", f"/exams/{exam_id}/activate")
    print(f"  -> Success! Exam Status is now: {activated_exam['status']}")

    # Step 7: Student Joins using the Join Code
    print("\n[7/15] Student Arjun Sharma accessing and joining the exam session...")
    student_email = f"arjun-{run_id}@example.com"
    student_access = call("POST", "/auth/student-access", {
        "student_name": "Arjun Sharma",
        "email": student_email,
    })
    student_token = student_access["token"]
    AUTH_TOKEN = student_token
    student_session = call("POST", "/sessions/join", {
        "join_code": join_code,
        "student_name": "Arjun Sharma",
        "email": student_email,
    })
    session_id = student_session["id"]
    print(f"  -> Success! Student Session Created (ID: {session_id}, Status: {student_session['status']})")

    # Step 8: Student Accepts Consent (DPDP Compliance)
    print("\n[8/15] Student accepting privacy and DPDP data consent...")
    consent_res = call("POST", f"/sessions/{session_id}/consent")
    print(f"  -> Success! Consent recorded: {consent_res['consent']} (Status: {consent_res['status']})")

    # Step 9: Student Completes Liveness Verification
    print("\n[9/15] Student performing blink liveness challenge verification...")
    blocked = call("GET", f"/sessions/{session_id}/questions", expected_status=422)
    assert "liveness" in str(blocked).lower(), blocked
    liveness_res = call("POST", f"/sessions/{session_id}/liveness", {
        "method": "mediapipe_ear", "blink_count": 2, "duration_ms": 2200, "threshold": 0.25
    })
    print(f"  -> Success! Liveness verified: {liveness_res['liveness']} (Status: {liveness_res['status']})")

    # Step 10: Fetch Questions for Student Session
    print("\n[10/15] Student fetching exam questions...")
    student_questions = call("GET", f"/sessions/{session_id}/questions")
    print(f"  -> Success! Loaded {len(student_questions)} questions for student.")

    # Step 11: Submit Student Answers
    print("\n[11/15] Submitting answers to questions...")
    # Answer first question
    answer_res_1 = call("POST", f"/sessions/{session_id}/answers", {
        "question_id": student_questions[0]["id"],
        "answer_text": "This is a source-locked student answer for Faraday's law of electromagnetism.",
        "time_spent_seconds": 45
    })
    print(f"  -> Success! Answer saved for Question 1.")

    # Step 12: End Student Session
    print("\n[12/15] Student completing and submitting the exam...")
    ended_session = call("POST", f"/sessions/{session_id}/end")
    print(f"  -> Success! Student Session status: {ended_session['status']}")

    # Step 13: Generate Integrity Report
    print("\n[13/15] Generating Integrity report...")
    AUTH_TOKEN = teacher_token
    report_res = call("POST", f"/sessions/{session_id}/reports/generate")
    print(f"  -> Success! Report Status: {report_res['status']}, URL: {report_res['download_url']}")

    # Step 14: Submit Appeal as Student
    print("\n[14/15] Student submitting an appeal regarding flags...")
    AUTH_TOKEN = student_token
    appeal_text = "I would like to state that my webcam visibility switches were due to adjustment of my reading posture."
    appeal_res = call("POST", f"/sessions/{session_id}/appeal", {
        "response": appeal_text
    })
    print(f"  -> Success! Appeal Status: {appeal_res['status']} (Response word count: {len(appeal_res['response'].split())})")

    # Step 15: Teacher Review Decision
    print("\n[15/15] Teacher reviewing appeal and saving final decision...")
    AUTH_TOKEN = teacher_token
    decision_res = call("PUT", f"/sessions/{session_id}/decision", {
        "decision": "clear",
        "teacher_note": "Postural adjustments verified. Integrity score resolved. Released grades."
    })
    print(f"  -> Success! Final Session Status: {decision_res['status']} (Grade Released: {decision_res['grade_released']})")

    print("\n======================================================================")
    print("      ALL END-TO-END FLOWS VERIFIED SUCCESSFULLY (NO ERRORS!)       ")
    print("======================================================================")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n[!] Test Suite Failed: {e}")
        sys.exit(1)
