-- Esquema: identificacion de usuarios por RUC (11 digitos) e historial conversacional.
-- Aplicar manualmente en el SQL editor de Supabase Studio, o via `supabase db push`
-- si se usa la Supabase CLI.
--
-- Este script arranca de cero: elimina usuarios/conversaciones/mensajes si existen
-- y los vuelve a crear con el esquema actual. NO toca documentos/pgvector (ver
-- 0002_pgvector_documentos.sql) - esa tabla es independiente de la identificacion
-- de usuarios.

drop table if exists mensajes cascade;
drop table if exists conversaciones cascade;
drop table if exists usuarios cascade;

create extension if not exists pgcrypto;

-- Datos de la empresa (razon_social, estado, etc.) se obtienen de OpenRuc al
-- registrar el RUC por primera vez (ver app/tools/consultar_api_externa.py) y
-- quedan cacheados aqui; en logins posteriores no se vuelve a llamar a la API.
create table usuarios (
    ruc text primary key check (ruc ~ '^[0-9]{11}$'),
    razon_social text,
    estado text,
    condicion text,
    direccion text,
    ubigeo text,
    source text,
    as_of date,
    created_at timestamptz not null default now()
);

create table conversaciones (
    id uuid primary key default gen_random_uuid(),
    usuario_ruc text not null references usuarios (ruc),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index conversaciones_usuario_ruc_idx
    on conversaciones (usuario_ruc);

create table mensajes (
    id uuid primary key default gen_random_uuid(),
    conversacion_id uuid not null references conversaciones (id),
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    created_at timestamptz not null default now()
);

create index mensajes_conversacion_id_idx
    on mensajes (conversacion_id);

-- El backend accede exclusivamente con la service role key (sin Supabase Auth de por
-- medio), por lo que RLS se habilita sin policies: bloquea cualquier acceso con la
-- anon key y no afecta al service role, que siempre bypassea RLS.
alter table usuarios enable row level security;
alter table conversaciones enable row level security;
alter table mensajes enable row level security;
