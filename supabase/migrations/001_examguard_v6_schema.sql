create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  display_name text not null,
  institute_name text,
  role text check (role in ('teacher', 'student')) not null,
  baseline_answer_count integer default 0,
  created_at timestamptz default now()
);

create table if not exists exams (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid references users(id) not null,
  title text not null,
  subject text,
  duration_min integer not null,
  total_marks integer not null,
  join_code char(6) unique not null,
  status text check (status in ('draft', 'active', 'ended', 'archived')) default 'draft',
  paper_config jsonb,
  config_validated boolean default false,
  questions_generated boolean default false,
  created_at timestamptz default now(),
  activated_at timestamptz,
  ended_at timestamptz
);

create table if not exists material_chunks (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid references exams(id) on delete cascade,
  material_filename text,
  chunk_text text not null,
  embedding vector(384),
  chapter_tag text,
  source_page integer,
  chunk_index integer,
  created_at timestamptz default now()
);

create index if not exists material_chunks_embedding_hnsw
  on material_chunks using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create table if not exists questions (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid references exams(id) on delete cascade,
  section_label text not null,
  question_text text not null,
  question_type text not null,
  options jsonb,
  correct_answer text,
  marks integer not null,
  blooms_level text,
  chapter_tag text,
  source_chunk_ids uuid[],
  groundedness_score float,
  teacher_modified boolean default false,
  created_at timestamptz default now()
);

create table if not exists exam_sessions (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid references exams(id) not null,
  student_id uuid references users(id) not null,
  status text check (status in ('joined', 'consented', 'active', 'paused', 'ended')) default 'joined',
  consent_given boolean default false,
  consent_given_at timestamptz,
  liveness_verified boolean default false,
  integrity_state text check (integrity_state in ('CLEAN', 'WATCH', 'WARN', 'FLAGGED')) default 'CLEAN',
  integrity_score float,
  integrity_ci integer,
  baseline_tier integer check (baseline_tier in (1, 2, 3)),
  review_status text check (review_status in ('pending', 'awaiting_response', 'decided')) default 'pending',
  teacher_decision text check (teacher_decision in ('cleared', 'confirmed_flag')),
  decision_at timestamptz,
  grade_released boolean default false,
  started_at timestamptz,
  ended_at timestamptz,
  unique(exam_id, student_id)
);

create table if not exists answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references exam_sessions(id) on delete cascade,
  question_id uuid references questions(id),
  answer_text text,
  selected_option text,
  time_spent_seconds integer,
  perplexity_score float,
  ai_detection_method text check (ai_detection_method in ('logprobs', 'entropy')),
  style_distance float,
  eval_score float,
  eval_reasoning text,
  source_chunk_ids uuid[],
  submitted_at timestamptz default now()
);

create table if not exists integrity_events (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references exam_sessions(id) on delete cascade,
  event_type text not null,
  event_data jsonb,
  score_impact float,
  severity text check (severity in ('info', 'warning', 'danger')),
  occurred_at timestamptz default now()
);

create table if not exists integrity_appeals (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references exam_sessions(id) unique,
  student_response text,
  submitted_at timestamptz,
  deadline_at timestamptz not null,
  teacher_note text,
  created_at timestamptz default now()
);

create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references users(id),
  session_id uuid references exam_sessions(id),
  action text not null,
  payload jsonb,
  created_at timestamptz default now()
);

alter table users enable row level security;
alter table exams enable row level security;
alter table material_chunks enable row level security;
alter table questions enable row level security;
alter table exam_sessions enable row level security;
alter table answers enable row level security;
alter table integrity_events enable row level security;
alter table integrity_appeals enable row level security;
alter table audit_log enable row level security;
