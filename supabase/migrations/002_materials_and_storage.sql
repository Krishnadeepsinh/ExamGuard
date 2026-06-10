create table if not exists materials (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid references exams(id) on delete cascade not null,
  filename text not null,
  status text check (status in ('processing', 'ready', 'failed')) default 'ready',
  chunk_count integer default 0,
  chapter_counts jsonb default '{}'::jsonb,
  storage_path text,
  created_at timestamptz default now()
);

alter table material_chunks
  add column if not exists material_id uuid references materials(id) on delete cascade;

alter table materials enable row level security;

create index if not exists materials_exam_id_idx on materials(exam_id);
create index if not exists material_chunks_material_id_idx on material_chunks(material_id);

insert into storage.buckets (id, name, public)
values ('materials', 'materials', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('reports', 'reports', false)
on conflict (id) do nothing;
