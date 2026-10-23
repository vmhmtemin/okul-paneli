-- =============================================================
--  Okul Paneli — görev senkronu (Supabase / Postgres)
--
--  Güvenlik modeli:
--   * Tablolara doğrudan erişim YOK (RLS açık, hiçbir policy yok,
--     anon/authenticated yetkileri geri alındı).
--   * Sayfa sadece aşağıdaki 4 fonksiyonu çağırabilir. Her çağrı
--     uzun, rastgele bir SYNC_KEY ister; veriler bu anahtarın
--     SHA-256 özetiyle etiketlenir. Anahtarı bilmeyen hiçbir satırı
--     göremez / değiştiremez.
--   * SYNC_KEY sadece şifreli panelin içinde durur.
-- =============================================================

create extension if not exists pgcrypto with schema extensions;

-- ------------------------------------------------------------ tablolar
create table if not exists public.panel_tasks (
  id          uuid primary key default gen_random_uuid(),
  owner_hash  text not null,
  title       text not null check (char_length(title) between 1 and 200),
  due_date    date,
  due_time    time,
  note        text check (note is null or char_length(note) <= 1000),
  done        boolean not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists panel_tasks_owner_idx on public.panel_tasks (owner_hash);

create table if not exists public.panel_mail_done (
  owner_hash  text not null,
  item_id     text not null check (char_length(item_id) between 1 and 40),
  done_at     timestamptz not null default now(),
  primary key (owner_hash, item_id)
);

alter table public.panel_tasks     enable row level security;
alter table public.panel_mail_done enable row level security;
revoke all on public.panel_tasks, public.panel_mail_done from anon, authenticated;

-- ------------------------------------------------------- yardımcılar
create or replace function public.panel_owner(p_key text)
returns text
language plpgsql
immutable
set search_path = ''
as $$
begin
  if p_key is null or char_length(p_key) < 32 then
    raise exception 'invalid sync key' using errcode = '28000';
  end if;
  return encode(extensions.digest(p_key, 'sha256'), 'hex');
end;
$$;

-- --------------------------------------------- 1) tüm veriyi getir
create or replace function public.panel_sync(p_key text)
returns json
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner text := public.panel_owner(p_key);
begin
  -- 120 günden eski tamamlanmış görevleri ve işaretleri temizle
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
       where d.owner_hash = v_owner), '[]'::json)
  );
end;
$$;

-- ------------------------------------- 2) görev ekle / güncelle
create or replace function public.panel_task_upsert(
  p_key text, p_id uuid, p_title text, p_due_date date, p_due_time time,
  p_note text, p_done boolean)
returns json
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner text := public.panel_owner(p_key);
  v_row   public.panel_tasks;
begin
  if (select count(*) from public.panel_tasks where owner_hash = v_owner) >= 1000 then
    raise exception 'task limit reached';
  end if;

  insert into public.panel_tasks as t (id, owner_hash, title, due_date, due_time, note, done)
  values (coalesce(p_id, gen_random_uuid()), v_owner, btrim(p_title), p_due_date, p_due_time,
          nullif(btrim(p_note), ''), coalesce(p_done, false))
  on conflict (id) do update
     set title = excluded.title, due_date = excluded.due_date, due_time = excluded.due_time,
         note = excluded.note, done = excluded.done, updated_at = now()
   where t.owner_hash = v_owner                     -- başkasının görevine dokunamaz
  returning * into v_row;

  if v_row.id is null then
    raise exception 'not found';
  end if;
  return json_build_object('id', v_row.id, 'updated_at', v_row.updated_at);
end;
$$;

-- --------------------------------------------------- 3) görev sil
create or replace function public.panel_task_delete(p_key text, p_id uuid)
returns void
language sql
security definer
set search_path = ''
as $$
  delete from public.panel_tasks
   where id = p_id and owner_hash = public.panel_owner(p_key);
$$;

-- ------------------------------ 4) mail görevini bitti/bitmedi yap
create or replace function public.panel_mail_done_set(p_key text, p_item_id text, p_done boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner text := public.panel_owner(p_key);
begin
  if p_done then
    insert into public.panel_mail_done (owner_hash, item_id) values (v_owner, p_item_id)
    on conflict do nothing;
  else
    delete from public.panel_mail_done where owner_hash = v_owner and item_id = p_item_id;
  end if;
end;
$$;

-- ------------------------------------------------------- yetkiler
revoke all on function public.panel_owner(text) from public, anon, authenticated;
revoke all on function public.panel_sync(text) from public;
revoke all on function public.panel_task_upsert(text, uuid, text, date, time, text, boolean) from public;
revoke all on function public.panel_task_delete(text, uuid) from public;
revoke all on function public.panel_mail_done_set(text, text, boolean) from public;

grant execute on function public.panel_sync(text) to anon;
grant execute on function public.panel_task_upsert(text, uuid, text, date, time, text, boolean) to anon;
grant execute on function public.panel_task_delete(text, uuid) to anon;
grant execute on function public.panel_mail_done_set(text, text, boolean) to anon;
