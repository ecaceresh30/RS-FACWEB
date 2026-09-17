-- Tabla de conocimiento (chunks de conocimiento.pdf) + busqueda por similitud via pgvector.
-- Aplicar manualmente en el SQL editor de Supabase Studio, o via `supabase db push`.
--
-- Dimension 1536 corresponde al modelo de embeddings por defecto usado en
-- app/knowledge/ingest.py (OpenAI text-embedding-3-small). Si se cambia el modelo
-- de embeddings, ajustar esta dimension y regenerar los embeddings existentes.

create extension if not exists vector;

create table if not exists documentos (
    id uuid primary key default gen_random_uuid(),
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(1536) not null,
    created_at timestamptz not null default now()
);

create index if not exists documentos_embedding_idx
    on documentos using hnsw (embedding vector_cosine_ops);

alter table documentos enable row level security;

create or replace function match_documents(
    query_embedding vector(1536),
    match_count int default 5
)
returns table (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
language sql stable
as $$
    select
        documentos.id,
        documentos.content,
        documentos.metadata,
        1 - (documentos.embedding <=> query_embedding) as similarity
    from documentos
    order by documentos.embedding <=> query_embedding
    limit match_count;
$$;
