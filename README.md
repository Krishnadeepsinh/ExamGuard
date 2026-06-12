# ExamGuard AI v6

ExamGuard AI is a syllabus-aware exam platform for teachers, coaching institutes, and students. Teachers upload their own material, generate grounded papers, monitor privacy-first online exams, and review integrity reports before releasing grades.

**Product positioning:** privacy-first online exams with AI-assisted paper generation and teacher-controlled integrity review.  
**Local app:** `frontend/`  
**Sample access:** teacher and student roles are available from the home page.  
**FAR AWAY 2026 alignment:** Examinations + Agentic & Autonomous Systems through a 10-agent LangGraph workflow.

## Quick Start

Apply Supabase migrations `001` through `004` in numeric order. Migration `004` adds the Auth profile trigger, ownership policies, and pgvector matching function.

### Simplest Windows start

```powershell
.\start_examguard.ps1
```

This starts the FastAPI backend on port `8000`, starts the React app on port `5173`, verifies backend health, and opens ExamGuard. It intentionally uses the local store so the complete demo works without waiting for hosted database setup.

Teacher flow: create exam -> upload required syllabus/material -> choose marks, difficulty, and paper type -> generate -> activate for students.

For hosted Supabase mode, apply migrations `001`, `002`, and `003` before setting `EXAMGUARD_STORE=supabase`.

Backend:

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Backend store mode:

- Default: `EXAMGUARD_STORE=local` uses the in-memory local store.
- Supabase: set `EXAMGUARD_STORE=supabase`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` in a local `.env` or deployment secret manager.
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend. The browser only talks to FastAPI.
- Upstash Redis: set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` backend-side only for live exam hot state.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

API smoke test:

```bash
python scripts/smoke_api.py
```

Seed sample data contract:

```bash
python scripts/seed_demo.py
```

## Sample Login

Teacher access:

- Email: `teacher@demo.examguard.ai`
- Password: `demo123`
- Opens: dashboard, paper config, live monitor, review, reports, settings.

Student access:

- Name: `Arjun Sharma`
- Join code: `PHY001` (fixed seed-only code; production codes are random)
- Optional email: `arjun@student.ai`
- Opens: consent, liveness, exam session, post-exam appeal, settings.

Role access is intentionally separated. A student cannot open teacher dashboards, and a teacher cannot enter student exam screens without switching accounts.

## The Problem For Institutes

- India conducts 90M+ exams per year.
- Teachers spend 6-8 hours setting one paper.
- AI-written answer submission is now a major cheating vector.
- Existing tools are expensive, cloud-heavy, and not designed for everyday institute workflows.

## What ExamGuard Does

- Upload teacher material and build a RAG corpus.
- Configure marks, sections, Bloom levels, question types, chapter weights, and difficulty.
- Choose MCQ-only, MCQ + QA, or mixed papers with MCQ, short/long answers, fill blanks, true/false, and essays.
- Generate grounded questions only from the uploaded syllabus/material. Outside facts, web knowledge, and model memory are not allowed.
- Run consent-first proctoring with raw webcam/audio kept local.
- Score integrity using behavioral, perplexity, stylometric, answer quality, and time anomaly factors.
- Route flagged cases into a 24-hour appeal workflow.

## Unified Integrity Thresholds

- CLEAN: score > 85
- WATCH: score 70-85
- WARN: score 50-70
- FLAGGED: score < 50

These thresholds are the final v6 source of truth.

## Architecture

Browser layer: React, MediaPipe WASM, Web Audio API, localStorage backup.  
API layer: FastAPI, REST endpoints, WebSocket rooms.  
Agent layer: 10 named LangGraph nodes in `backend/agents/`.  
Data layer: Supabase PostgreSQL, pgvector, Supabase Storage, Upstash Redis.  
Generation layer: Gemini API only for the current build. If Gemini is unavailable, generation pauses with a retryable teacher-facing error; the system does not silently fabricate questions.

## 10 Agents

See [AGENTS.md](AGENTS.md).

## Hackathon Submission Note

This repository is also prepared for FAR AWAY 2026. The product itself is designed to stand on its own for teachers and students; the submission evidence lives in `AGENTS.md`, `docs/`, screenshots, and the final product walkthrough video.

## NCERT Legal Note

NCERT textbooks are published by the Government of India and are freely available for educational use via `ncert.nic.in`. Sample assets must cite NCERT clearly and must not claim an MIT or software license for textbook content.

## DPDP Compliance

See [docs/dpdp-compliance.md](docs/dpdp-compliance.md) and [SECURITY.md](SECURITY.md).
