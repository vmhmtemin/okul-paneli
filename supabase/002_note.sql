-- =============================================================
--  Ek: Not kağıdı (panelin en üstündeki serbest not) — schema.sql'den sonra çalıştır
-- =============================================================
create table if not exists public.panel_notes (
  owner_hash  text primary key,
  body        text not null default '' check (char_length(body) <= 2000),
  updated_at  timestamptz not null default now()
);
alter table public.panel_notes enable row level security;
revoke all on public.panel_notes from anon, authenticated;

create or replace function public.panel_note_set(p_key text, p_body text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner text := public.panel_owner(p_key);
begin
  insert into public.panel_notes (owner_hash, body) values (v_owner, coalesce(p_body, ''))
  on conflict (owner_hash) do update set body = excluded.body, updated_at = now();
end;
$$;

-- panel_sync artık notu da döndürüyor
create or replace function public.panel_sync(p_key text)
returns json
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner text := public.panel_owner(p_key);
begin
  delete from public.panel_tasks
   where owner_hash = v_owner and done and updated_at < now() - interval '120 days';
  delete from public.panel_mail_done
   where owner_hash = v_owner and done_at < now() - interval '120 days';

  return json_build_object(
    'tasks', coalesce((
      select json_agg(json_build_object(
               'id', t.id, 'title', t.title, 'due_date', t.due_date,
               'due_time', to_char(t.due_time, 'HH24:MI'), 'note', t.note,
               'done', t.done, 'updated_at', t.updated_at)
             order by t.due_date nulls last, t.due_time nulls last, t.created_at)
        from public.panel_tasks t where t.owner_hash = v_owner), '[]'::json),
    'mail_done', coalesce((
      select json_agg(d.item_id) from public.panel_mail_done d
       where d.owner_hash = v_owner), '[]'::json),
    'note', (select n.body from public.panel_notes n where n.owner_hash = v_owner)
  );
end;
$$;

revoke all on function public.panel_note_set(text, text) from public;
grant execute on function public.panel_note_set(text, text) to anon;
