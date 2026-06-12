-- ExamGuard v6 production auth and pgvector retrieval support.
create or replace function public.match_material_chunks(
  query_embedding vector(384),
  target_material_id uuid,
  match_count integer default 8
)
returns table (
  id uuid,
  chunk_text text,
  chapter_tag text,
  source_page integer,
  similarity float
)
language sql stable
as $$
  select mc.id, mc.chunk_text, mc.chapter_tag, mc.source_page,
         1 - (mc.embedding <=> query_embedding) as similarity
  from public.material_chunks mc
  where mc.material_id = target_material_id and mc.embedding is not null
  order by mc.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  insert into public.users (id, email, display_name, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data->>'role', 'student')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_auth_user();

create policy "users read own profile" on public.users for select using (auth.uid() = id);
create policy "users update own profile" on public.users for update using (auth.uid() = id);
create policy "teachers own exams" on public.exams for all using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());
create policy "teachers read own materials" on public.material_chunks for select using (
  exists (select 1 from public.exams e where e.id = exam_id and e.teacher_id = auth.uid())
);
create policy "teachers read own questions" on public.questions for select using (
  exists (select 1 from public.exams e where e.id = exam_id and e.teacher_id = auth.uid())
);
