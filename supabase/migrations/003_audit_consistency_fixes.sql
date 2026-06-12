-- Consistency fixes from the v6.0.1 product/document audit.

alter table questions
  add column if not exists section_index integer,
  add column if not exists question_index integer,
  add column if not exists low_groundedness boolean default false,
  add column if not exists generation_attempts integer default 1;

create unique index if not exists questions_exam_section_question_unique
  on questions(exam_id, section_index, question_index)
  where section_index is not null and question_index is not null;

alter table integrity_appeals
  add column if not exists status text default 'awaiting_response',
  add column if not exists teacher_response text,
  add column if not exists resolved_at timestamptz;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'integrity_appeals_status_check'
  ) then
    alter table integrity_appeals
      add constraint integrity_appeals_status_check
      check (status in ('awaiting_response', 'submitted', 'expired_no_response', 'decided'));
  end if;
end $$;

create unique index if not exists answers_session_question_unique
  on answers(session_id, question_id);

alter table exam_sessions drop constraint if exists exam_sessions_review_status_check;
alter table exam_sessions
  add constraint exam_sessions_review_status_check
  check (review_status in ('pending', 'awaiting_response', 'awaiting_teacher_decision', 'decided'));

comment on column questions.low_groundedness is
  'True only when groundedness remains below threshold after all regeneration attempts.';

comment on column integrity_appeals.status is
  'Expiry never confirms a flag automatically; expired cases await a teacher decision.';
