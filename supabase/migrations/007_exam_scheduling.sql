alter table exams drop constraint if exists exams_status_check;
alter table exams add constraint exams_status_check
  check (status in ('draft', 'scheduled', 'active', 'paused', 'ended', 'archived'));

alter table exams add column if not exists scheduled_start_at timestamptz;
alter table exam_sessions add column if not exists locked_for_review boolean not null default false;

create index if not exists exams_scheduled_start_idx
  on exams(status, scheduled_start_at)
  where status = 'scheduled';
