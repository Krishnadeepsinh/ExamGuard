# ExamGuard v6 Canonical Product Decisions

This file resolves ambiguities found during the June 11, 2026 master-document audit. When older documentation conflicts with this file or current code, this file and the tested implementation take precedence.

## Integrity Tiers

| Tier | Baseline | Stylometric weight | Confidence interval | Rule |
|---|---:|---:|---:|---|
| Tier 1 | 3+ prior exams | 25% | +/-7 | Full five-factor model |
| Tier 2 | 1-2 prior exams | 10% | +/-15 | Partial baseline; remaining weight redistributed |
| Tier 3 | First exam | Disabled | Not shown | Four-factor model; baseline starts building |

Rahul is the canonical Tier 3 scenario: score approximately 65, status WARN, amber tile, no stylometric factor.

## Appeal Expiry

- FLAGGED opens a 24-hour response window.
- No response never auto-confirms a flag.
- At expiry, status becomes `expired_no_response` and the case moves to `awaiting_teacher_decision`.
- Grade remains held until a teacher records `cleared` or `confirmed_flag` with a note.

## Answer Autosave And Rate Limits

- Autosave is an idempotent upsert by `(session_id, question_id)`.
- The client saves locally first, then syncs to the API.
- On HTTP 429 or network failure, localStorage keeps the newest answer and retries with exponential backoff.
- The answer endpoint limit is per session/IP, not per individual answer.
- A rate-limit response never deletes or clears local student input.

## Demo Join Code

`PHY001` is intentionally fixed by the seed script for a repeatable demo. Production exam creation uses a collision-checked random six-character uppercase alphanumeric code. Clones always receive a new random code.

## Clone Semantics

Cloning creates a new draft exam. It copies title with a `Copy` suffix, subject, duration, total marks, paper configuration, and links to teacher-owned source materials. It does not copy sessions, answers, integrity events, reports, appeals, activation timestamps, or the original join code. Generated questions are not copied by default and must be regenerated or explicitly imported by a future feature.

## Source-Locked Question Generation

- Every generation call requires uploaded material and retrieved source chunks.
- Gemini receives only the retrieved chunks and strict source-lock instructions.
- If evidence is insufficient, generation returns `INSUFFICIENT_SOURCE`; it does not use model memory or web knowledge.
- Groundedness below 0.72 triggers up to three attempts.
- Remaining failures are stored with `low_groundedness=true` and require teacher review before activation.

## Microphone Unavailable

Microphone permission is optional. If denied or unavailable, audio events are marked unavailable rather than suspicious. No integrity penalty is applied solely for missing audio. Behavioral scoring is normalized across available signals and the teacher tile shows `Audio unavailable`.

## Live Data Contract

WebSocket/Redis push is primary. `GET /exams/{id}/live` is only for initial hydration, reconnect recovery, and fallback polling after WebSocket failure. It must not be polled continuously while the socket is healthy.

## Agent Flow

```text
Upload material
  -> Material Ingestion Agent
  -> chunking / chapter map / embeddings

Save paper configuration
  -> Paper Config Agent
  -> Question Generation Agent
  -> groundedness + diversity validation

Student exam live
  -> Proctoring Agent
  -> Security Agent + Stylometric Agent
  -> Orchestrator Agent
  -> Review Agent only when FLAGGED

Exam ends
  -> Evaluation Agent
  -> Report Agent
  -> Teacher review / grade release
```

## Alternatives Considered

| Choice | Selected | Alternative | Reason |
|---|---|---|---|
| Database/RAG | Supabase Postgres + pgvector | Firebase, Pinecone | Relational exam data, RLS, storage, auth, and vectors in one platform |
| Agent orchestration | LangGraph StateGraph | CrewAI, AutoGen | Explicit state, deterministic routing, resumability, and traceability |
| Backend | FastAPI | Node/Express | Strong typed validation, Python AI ecosystem, ReportLab and ML libraries |
| Realtime hot state | Upstash Redis | Database polling | Low-latency ephemeral events with TTL; Supabase remains system of record |
| Generation | Gemini API | Local Ollama | Current build prioritizes simpler deployment; failure pauses generation instead of silently degrading |
