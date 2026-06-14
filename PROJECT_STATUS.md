# ExamGuard AI v6 Project Status

Last updated: 2026-06-13

Repository target: `https://github.com/Krishnadeepsinh/ExamGuard.git`

Git remote: `origin` points to repository target; production fixes are committed and pushed through `96d3719` before this current hardening pass.

## 2026-06-13 Production Hardening Pass

- Added migration `006_production_integrity_hardening.sql`.
- Activated papers capture an immutable versioned snapshot.
- Session deadlines are server-authoritative; expired attempts reject answer writes.
- Fixed session timestamps that incorrectly reused the 24-hour appeal deadline helper.
- Answer retries use idempotency keys.
- Integrity factors persist in Supabase and events use sequence-numbered SHA-256 hash chains.
- Liveness uses per-student calibration plus face size and centering gates.
- Preflight checks secure context, camera support, network, and offline storage.
- Monitoring detects sustained absence, multiple faces, frozen frames, and sustained looking away while raw media stays local.
- Apply Supabase migration `006` before deploying the matching backend version.
- Removed production login/demo identity defaults and sample credential exposure.
- Removed 25-character minimum answer gate; unanswered questions remain visible in submit summary.
- Added continuous on-device face-presence monitoring during active exams; raw frames never upload.
- Added debounced `face_missing`, `multiple_faces`, and `monitoring_interrupted` evidence events.
- Isolated blur, right-click, small paste, or one tab event cannot auto-flag a student.
- Added server-side proctoring event allowlist.
- Replaced fabricated integrity factor values with neutral unmeasured values and Tier 3 first-exam handling.
- Added strict generated-question validation and one Gemini repair retry.
- Removed placeholder paper generation; failed quality checks preserve existing paper and return a retryable error.
- Updated reports to avoid unsupported claims of continuous proof, zero hallucinations, or automatic guilt.
- Added focus-visible styling, reduced-motion support, safer form autocomplete, and live presence status.

## 2026-06-11 Production Completion Pass

- Gemini 2.5 Flash rotates across four backend-only keys with cooldown and failover.
- Supabase persistence and Upstash Redis are active from ignored `backend/.env`.
- LangGraph is an executable 10-node `StateGraph`; proof endpoint: `/api/v1/agents/graph`.
- Teacher monitor uses WebSocket snapshots, reconnect backoff, and Redis event persistence.
- Material chunks receive normalized 384-dimension embeddings and source-only similarity ranking.
- Teacher login/signup uses Supabase Auth; student exam entry remains join-code based.
- Blink liveness uses MediaPipe Face Landmarker locally in-browser; frames are never uploaded.
- Apply `supabase/migrations/004_auth_vectors_production.sql` before deployment.
- Backend tests and frontend production build pass.

## 2026-06-12 Deep Audit

- Full hosted workflow passed: login, exam creation, material upload, configuration, grounded Gemini generation, activation, student join, consent, liveness evidence, questions, answer save, submit, report, appeal, and teacher decision.
- Negative gates passed: missing auth, wrong teacher ownership, invalid join code, questions before liveness, answers before liveness, empty liveness evidence, and unauthorized WebSocket.
- Proctoring events now recalculate deterministic integrity; tab-hide plus blur moved a live session from CLEAN to WATCH and appeared in teacher monitor.
- Removed fake dashboard, monitor, report, review, completion, camera, and student fallback data.
- Consent now requires scrolling to bottom. Exam start remains disabled until two-blink MediaPipe liveness succeeds and backend accepts evidence.
- Material ingestion changed from 32-token chunks to 384-token chunks, reducing a test upload from 4,641 chunks to 14.
- Teacher APIs and monitor WebSockets now verify Supabase tokens and exam ownership.
- Added Render Docker deployment and Vercel SPA configuration.
- Remaining external action: apply migration `004_auth_vectors_production.sql`, configure deployment environment variables, and run camera test on a device with a webcam.

### Current State

This repository contains a working, demo-ready ExamGuard AI v6 vertical slice. React, FastAPI, Supabase, Gemini, Upstash, LangGraph, pgvector-ready embeddings, WebSockets, and Supabase Auth are integrated. Deployment and migration 004 remain external release actions.

## Work Completed

- Completed hosted Supabase browser/API test for SQL exam `EPPJGS` using `material.pdf`:
  - Created 100-mark, 120-minute SQL exam.
  - Extracted 733 words/chunks from the supplied PDF and mapped source sections.
  - Generated and stored 60 questions, activated exam, joined from student flow, recorded consent/liveness, saved an answer, submitted, and verified teacher monitor/report output.
  - Stored uploaded source file in private Supabase `materials` bucket and persisted its `storage_path`.
  - Persisted structured integrity events in Supabase and removed invented monitor events/counts.
- Removed hardcoded Physics/40-question fallback from student exam. Question load failures now show a real retry state.
- Regeneration now replaces draft questions and is blocked after students join.

- Repaired the teacher paper lifecycle: newly created exams now open their own configuration instead of loading the first exam.
- Made syllabus/material upload mandatory for generation and removed fake preloaded material state.
- Added automatic exact-mark templates for MCQ, MCQ + QA, and Mixed papers.
- Added real generated-question preview/list and explicit exam activation for student joining.
- Added persistent light/dark themes and verified mobile sizing and overflow.
- Added `start_examguard.ps1` for one-command local startup with backend health verification.

- Completed the June 11 consistency and policy audit:
  - Explicitly labels Rahul as `WARN`, score about 65, Tier 3.
  - Defines Tier 2 as reduced-confidence stylometry with a 10% weight and a +/-15 confidence interval.
  - Keeps expired appeals in teacher review; expiry never auto-confirms a flag.
  - Makes answer saves idempotent with one answer per session/question.
  - Defines clone behavior, source-lock behavior, microphone denial behavior, and seeded join-code behavior.
- Added `supabase/migrations/003_audit_consistency_fixes.sql` for question ordering, generation metadata, appeal state, and answer uniqueness.
- Added canonical implementation references:
  - `docs/product-decisions.md`
  - `docs/detailed-sprint-plan.md`
  - `docs/screen-specs-9-11.md`
- Corrected the master product document with a linked table of contents, PostgreSQL placeholders, demo-only credential notes, correct 80-mark wording, agent flow, and alternatives considered.
- Added focused policy tests in `backend/tests/test_integrity_and_policy.py`.

- Created React + Vite + TypeScript frontend in `frontend/`.
- Built route-style product screens for:
  - Home
  - Role-based login
  - Teacher dashboard
  - Paper configuration
  - Live monitor
  - Student consent
  - Blink liveness
  - Student exam session
  - Student post-exam appeal
  - Teacher review
  - Reports
  - Account settings/password reset
- Connected React state to backend API endpoints (`api.ts`):
  - **Auth:** Real signup/login API requests for both teacher and student roles.
  - **Teacher Dashboard:** Real creation, cloning, deletion, and selection of exams.
  - **Paper Configuration:** OCR-fallback file uploading, target marks config, and source-locked question generation.
  - **Live Monitor:** Active polling (every 4s) of student sessions, dynamically calculating warning/flagged counts and class average score. Added toggle-pause/resume and end exam actions.
  - **Student Gate:** Consent recording, blink liveness verification, and fetching real questions.
  - **Student Exam:** Working timer countdown loaded from exam duration, per-question auto-save (every 10s), per-question navigation saves, immediate MCQ option saves, and dynamic Submit dialog counts.
  - **Post-Exam:** Submitting student appeals to the backend and updating states.
  - **Teacher Review:** Loading flagged queue dynamically, showing the student's real appeal explanation, and saving decisions ("Clear and release" / "Confirm flag") with required notes.
  - **Reports:** Loading exam statistics dynamically, CSV downloads via dynamic stream, and student-level PDF report downloads.
- Connected the active polling message banner to replace the disconnected WebSocket notification.
- Fixed all TypeScript and CSS compilation errors so the frontend builds cleanly (`npm run build`).
- Updated the backend store with parity methods and unified implementations for both local and Supabase stores.
- Successfully verified the entire end-to-end integration flow via `scripts/comprehensive_test.py` (passing all 15 stages).
- Added final v6 integrity threshold source of truth:
  - CLEAN > 85
  - WATCH 70-85
  - WARN 50-70
  - FLAGGED < 50
- Added backend scaffold in `backend/`.
- Added working local API routes in `backend/main.py` for auth, exams, materials, source-locked paper config/generation, sessions, answers, appeals, decisions, and reports.
- Added `backend/store.py` as a local in-memory store so the core product flow can run before Supabase/Redis are connected.
- Added `backend/config.py` and `backend/supabase_store.py` for Supabase backend integration using environment variables only.
- Added `backend/redis_client.py` for optional Upstash Redis REST hot state, using environment variables only.
- Added `supabase/migrations/002_materials_and_storage.sql` for material upload records, chunk linkage, and private storage buckets.
- Service-role key must remain backend-only. Do not hardcode it, commit it, or expose it through Vite/frontend environment variables.
- Upstash Redis token must remain backend-only. Do not hardcode it, commit it, or expose it through frontend environment variables.
- Added all 10 named agent modules in `backend/agents/`.
- Added `backend/agents/graph.py` as LangGraph topology reference.
- Added `backend/agents/llm_router.py` and `bloom_templates.py`.
- Tightened backend paper/question agent contracts so question generation requires uploaded material and must not use outside facts, web knowledge, or model memory.
- Added frontend API client in `frontend/src/api.ts`.
- Connected frontend login/join and paper upload/config/generation actions to the local FastAPI backend.
- Added `scripts/smoke_api.py` to verify the full local API flow.
- Added Supabase migration in `supabase/migrations/001_examguard_v6_schema.sql`.
- Added `scripts/seed_demo.py` dry-run sample data seeding contract.
- Added submission docs:
  - `README.md`
  - `AGENTS.md`
  - `SECURITY.md`
  - `CONTRIBUTING.md`
  - `docs/dpdp-compliance.md`
  - `docs/architecture.md`
  - `docs/architecture.png`
- Added `docker-compose.yml`, `.env.example`, and GitHub Actions workflows.
- Captured demo screenshots in `docs/demo-screenshots/`.
- Added `hardware/README.md` for Round 2 hardware path.

## Sample Login

Teacher:

- Email: `teacher@demo.examguard.ai`
- Password: `ExamGuard-Demo-2026!` unless `DEMO_TEACHER_PASSWORD` is set differently

Student:

- Name: `Arjun Sharma`
- Join code: `PHY001` (fixed seed-only code)
- Optional email: `arjun@student.ai`

## Verified

Commands run successfully:

```bash
cd frontend
npm run build
```

```bash
python scripts/comprehensive_test.py
python -m compileall backend scripts
python -m unittest discover -s backend/tests -v
python scripts/seed_demo.py
```

Local frontend verified at:

```text
http://127.0.0.1:5173
```

Screenshots generated for desktop and mobile flows in `docs/demo-screenshots/`.

## What Still Needs Real Backend Work

- Apply Supabase migration `003_audit_consistency_fixes.sql` in the hosted project (and confirm `001`/`002` are already applied).
- Connect auth to Supabase Auth instead of the current service-backed demo user flow.
- Duplicate all frontend validations on the backend because client validation can be bypassed.
- Add Zod/Pydantic request schemas for every API route.
- Implement real DB writes for exams, sessions, answers, reports, and appeals.
- Implement real RLS policies beyond schema enabling.
- Wire file upload to Supabase Storage.
- Implement real PDF parsing/OCR/embedding pipeline.
- Implement actual LangGraph runtime using the existing agent modules as contracts.
- Connect Gemini generation to the live provider and verify retry/error handling. Ollama is intentionally excluded from the current build.
- Current configured Gemini key returns `API_KEY_INVALID`; a valid Google AI Studio Gemini API key is required for real LLM-generated SQL wording.
- Replace manual/demo blink control with real MediaPipe EAR detection before claiming automated liveness.
- Add Redis state writes and WebSocket events.
- Deploy frontend/backend and update README live URLs.

## Next Recommended Steps

1. Apply and verify all Supabase migrations, especially migration `003`.
2. Replace demo auth/storage with Supabase Auth, Storage, and RLS-backed persistence.
3. Implement the live Gemini-only RAG pipeline and 10-node LangGraph runtime.
4. Add Redis/WebSocket live monitoring and run deployment load/security checks.
5. Commit, push, deploy, then record the 4:30 product walkthrough and LangGraph Studio proof.

## Notes For Future Agents

- Do not reintroduce the old `FLAGGED <60` threshold.
- Keep teacher and student areas role-separated.
- Keep this file updated after every major implementation batch.
- The current implementation favors offline-first development ease (`EXAMGUARD_STORE=local`) while maintaining a direct upgrade path to production Supabase storage.

## 2026-06-12 Production Audit

Completed:

- Fixed paper-config 500 caused by calling a protected FastAPI route internally.
- Blocked activation when generated question count is zero.
- Fixed MediaPipe flow: second valid blink now saves liveness proof and enters exam automatically.
- Split syllabus and study-material upload controls. Either source works alone; both are combined for retrieval.
- Tagged source type without a database migration by using private Storage paths (`exam/syllabus/...` and `exam/material/...`).
- Reworked Gemini and fallback prompts so questions test concepts instead of asking what an uploaded document says.
- Added regression tests for empty activation and distinct syllabus/material sources.
- Verified backend: `14 passed`.
- Verified frontend: production build passes; ESLint has zero errors (existing warnings remain).

Deployment follow-up:

- Render and Vercel must finish deploying the latest commit before production browser verification.
- Supabase migration `005_pause_exam_status.sql` still must be applied manually for pause/resume support.

## 2026-06-12 Student Flow Hardening

- Replaced fixed blink threshold with 24-frame per-face calibration, adaptive close/reopen thresholds, 15-second window, closure-duration filtering, and GPU-to-CPU fallback.
- Liveness automatically saves evidence and enters exam after blink two.
- Removed Home/login navigation after authentication.
- Added Arjun, Priya, and Rahul student demo identity quick-fill controls.
- Removed prefilled exam answers and appeal text.
- Isolated answer backups per session; students cannot inherit another student's local answers.
- Added per-tab student session ownership and duplicate-tab reset while preserving normal reload.
- Strengthened Gemini paper prompt for self-contained questions, plausible MCQ distractors, marking guides, uniqueness, and no source-document wording.
- Added deterministic critical-pattern escalation for repeated tab hiding plus multiple paste/fullscreen/phone vectors.
- Production simulation: clean student scored `91.4 CLEAN`; risk student escalated to `45 FLAGGED` after critical multi-vector behavior.
- Backend test suite: `15 passed`; frontend production build passed.

## 2026-06-13 Review, Grading, And Class Reports

- Teacher review now identifies selected exam, student, AI marks, integrity status, and release state in one summary.
- Review queue includes completed CLEAN students as well as WARN/FLAGGED sessions.
- Removed fake hardcoded anomaly claims; UI shows actual structured event counts only.
- Added deterministic objective grading and transparent marking-guide coverage fallback for subjective answers.
- Grades remain hidden from students until teacher clears or confirms review and releases result.
- Student result page polls for teacher decision and displays marks/percentage after release.
- Added one exam-level PDF and CSV containing every student, marks, integrity, cheat-review state, and release status.
- Paste evidence records question ID, character count, bulk-paste flag, and fullscreen state; clipboard content and screenshots are not stored.
- Added mobile account name and logout controls for teacher and student.
- Backend test suite: `17 passed`; frontend production build passes; ESLint has zero errors.

## 2026-06-13 Exam Lifecycle And Student Access Hardening

- Fixed production Supabase integrity reads by normalizing database session rows before returning status.
- Draft/generated papers now reject student joins; only live (`active`) exams accept a join code.
- Added reviewed-paper scheduling and automatic activation when the scheduled time is reached.
- Added explicit Go Live Now and Schedule controls after complete paper review.
- Added destructive delete confirmation naming the exam and affected data.
- Increased upload/generation request timeout to 120 seconds and converted generation/storage failures into actionable API messages.
- Added signed student browser access tokens and a My Results path that does not require re-entering an exam code.
- Added deterministic attempt locking only after repeated, independent critical signals; one tab change, focus loss, or ordinary paste cannot lock a student.
- Added `007_exam_scheduling.sql`; it must be applied before deploying this batch.
- Backend test suite: `27 passed`; Python compilation and frontend production build pass; ESLint has zero errors (34 existing warnings).

## 2026-06-13 Exam-Wise Monitoring Redesign

- Rebuilt the teacher live monitor around the selected exam rather than generic global metrics.
- Added exam title, subject, duration, marks, join code, lifecycle status, and WebSocket state to a single command header.
- Added compact student, average-integrity, and attention KPIs plus a proportional CLEAN/WATCH/WARN/FLAGGED distribution.
- Grouped filter/sort controls separately from pause, alerts, and destructive end-exam commands.
- Added a sticky student evidence inspector with identity, score factors, progress, consent, and event count.
- Added mobile monitor layouts with wrapping controls, two-column KPIs, and full-width actions.
- Frontend production build passes; ESLint has zero errors (existing warnings remain).

## 2026-06-13 Paper Generation Reliability

- Reproduced the reported deployed error against the exact SQL draft and confirmed the backend completed all 25 grounded MCQs in about 60 seconds after the browser had failed.
- Reduced ordinary section generation from three sequential Gemini requests to one request for up to 25 questions.
- Added an explicit Gemini output-token budget for complete section responses.
- Increased long-operation browser timeout to 180 seconds and added one safe retry for generation and uploads.
- Added teacher-authenticated generated-question recovery; completed papers reappear after reload or a lost response.
- Generation errors now attempt backend recovery before displaying failure.
- Material storage upload/delete failures return actionable 503 responses instead of unhandled server errors.
- Added consistent timeout/offline handling to report downloads.
- Backend test suite: `29 passed`; frontend production build passes.
