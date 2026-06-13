-- Keep generated papers distinct from unfinished drafts.
alter table exams drop constraint if exists exams_status_check;
alter table exams add constraint exams_status_check
  check (status in ('draft', 'generated', 'scheduled', 'active', 'paused', 'ended', 'archived'));

update exams
set status = 'generated'
where status = 'draft'
  and questions_generated = true;
