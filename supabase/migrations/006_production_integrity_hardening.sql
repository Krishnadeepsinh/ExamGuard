-- Production hardening: immutable paper snapshots, authoritative deadlines,
-- transparent integrity factors, retry-safe answers, and tamper-evident events.

alter table exams
  add column if not exists paper_snapshot jsonb,
  add column if not exists paper_version integer not null default 0;

alter table exam_sessions
  add column if not exists expires_at timestamptz,
  add column if not exists integrity_factors jsonb not null default '{}'::jsonb;

alter table answers
  add column if not exists idempotency_key text;

create unique index if not exists answers_session_idempotency_unique
  on answers(session_id, idempotency_key)
  where idempotency_key is not null;

alter table integrity_events
  add column if not exists sequence_number bigint,
  add column if not exists previous_hash text,
  add column if not exists event_hash text;

create unique index if not exists integrity_events_session_sequence_unique
  on integrity_events(session_id, sequence_number)
  where sequence_number is not null;

comment on column exams.paper_snapshot is
  'Immutable question/config snapshot captured when an exam is activated.';
comment on column exam_sessions.expires_at is
  'Server-authoritative attempt deadline. Clients may display but cannot extend it.';
comment on column integrity_events.event_hash is
  'SHA-256 chain hash over the previous hash and canonical event payload.';
