-- Allow teacher pause/resume controls to persist in production.
alter table public.exams drop constraint if exists exams_status_check;
alter table public.exams
  add constraint exams_status_check
  check (status in ('draft', 'active', 'paused', 'ended', 'archived'));
