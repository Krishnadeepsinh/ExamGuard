# ExamGuard v6 Detailed Sprint Execution Plan

## Sprint 1 - Foundation, Auth, Database, Ingestion

| Task | Implementation | Acceptance |
|---|---|---|
| Repository foundation | React/Vite frontend, FastAPI backend, environment validation, CI | Clean install builds frontend and imports backend |
| Authentication | Supabase teacher auth; transient student join identity | Teacher session persists; students cannot access teacher routes |
| Database | Apply migrations 001-003 with RLS and private buckets | Tables, indexes, constraints, and buckets exist |
| Material upload | PDF/DOCX/TXT, 50MB max, 10 files/exam | Invalid type/size rejected; valid file has processing state |
| Ingestion | PyMuPDF/DOCX/TXT extraction, OCR fallback, chunking, chapter tags | Digital and scanned fixture both produce searchable chunks |
| Embeddings | 384-dimensional embeddings in pgvector HNSW | Top-k query returns chapter-filtered chunks under target latency |

## Sprint 2 - Paper Configuration And Generation

| Task | Implementation | Acceptance |
|---|---|---|
| Exam configuration | Total marks, duration, overall difficulty, paper mode | Values persist and reload |
| Section builder | Type, count, marks, Bloom level, chapter, level override | Maximum 10 sections; invalid rows display inline errors |
| Marks tally | Recalculate every edit | Generate enabled only when exact total matches |
| Coverage validation | Minimum candidate chunks per requested question | Insufficient chapter material blocks generation |
| Source-locked generation | Gemini prompt receives retrieved chunks only | Every question has source chunk/page IDs |
| Groundedness retry | Retry below 0.72 up to three times | Final low result stored with warning flag |
| Diversity | Reject cosine similarity above 0.85 | Duplicate-like questions regenerated |
| Teacher preview | Edit, remove, regenerate, approve questions | Modified questions marked teacher-modified |

## Sprint 3 - Student Entry And Exam Session

| Task | Implementation | Acceptance |
|---|---|---|
| Join flow | Fixed seed code for demo, random code in production | Invalid/inactive/ended codes return distinct messages |
| Consent | Four plain-language items, scroll gate | Continue disabled until full consent review |
| Permissions | Camera required for liveness; microphone optional | Audio unavailable causes no integrity penalty |
| Liveness | Two blinks in eight seconds, three retries | Failure notifies teacher and allows warned continuation |
| Exam UI | Question types, palette, mark-for-review, timer | Keyboard and mobile flows remain usable |
| Autosave | Local first, API upsert, reconnect retry | Latest local answer wins after disconnect |
| Submission | Answered/marked/unanswered summary | Auto-submit at zero preserves all saved input |

## Sprint 4 - Live Monitoring

| Task | Implementation | Acceptance |
|---|---|---|
| Event capture | Tab, gaze, paste, audio availability, keyboard burst | Structured events only; no raw media leaves browser |
| Hot state | Upstash Redis REST keys with exam-duration TTL | Join/consent/liveness/answer events appear in live feed |
| Live transport | WebSocket primary, REST hydration/recovery fallback | Teacher update arrives within three seconds |
| Tiles | Status, score, tier, consent, progress, event count | Risk sorting puts FLAGGED first |
| Exam controls | Pause/resume/end confirmations | All active clients receive state change |

## Sprint 5 - Integrity Intelligence

| Task | Implementation | Acceptance |
|---|---|---|
| Behavioral score | Documented event deductions and normalization | Missing optional audio is neutral |
| Security signal | Gemini-independent statistical detector | Detection method stored with every analyzed answer |
| Stylometric tiers | Tier 1 full, Tier 2 10%, Tier 3 disabled | CI and factor display match canonical decisions |
| Orchestrator | Deterministic weighted scoring | Threshold boundary tests pass exactly |
| Review trigger | FLAGGED opens appeal state | No LLM can directly punish or release grades |

## Sprint 6 - Evaluation, Reports, Appeals

| Task | Implementation | Acceptance |
|---|---|---|
| Grading | Deterministic objective and rubric-based subjective grading | Every score includes reasoning/source references |
| Reports | Student PDF, CSV, batch ZIP, print layout | Individual PDF generated in under 10 seconds |
| Appeal | 24-hour response, 200-word maximum | Expiry never auto-confirms flag |
| Teacher decision | Clear/confirm with required note and audit log | Grade release follows explicit teacher decision |
| Analytics | Distribution, median, flagged count | Empty/loading/error states covered |

## Sprint 7 - Production And Submission

| Task | Implementation | Acceptance |
|---|---|---|
| Security | Secret scan, CORS, rate limits, RLS tests | No service keys or tokens in client bundle/repository |
| Deployment | Vercel frontend, Render backend, Supabase, Upstash | Public URLs pass health and end-to-end smoke tests |
| CI | Build, compile, unit, integration, migration checks | Main branch remains green |
| Seed | Repeatable teacher/exam/student/report scenarios | Fresh environment ready in under five minutes |
| Documentation | README, architecture, decisions, screenshots | Claims match actual implementation |
| Demo | Product-first walkthrough under 4:30 | Shows source citations, live event, report, and agent graph |
