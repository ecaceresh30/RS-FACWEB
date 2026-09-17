"""Script standalone de ingesta: conocimiento.pdf -> chunks -> embeddings -> Supabase/pgvector.

Uso:
    python -m app.knowledge.ingest [ruta_al_pdf]

Si no se indica ruta, se usa app/knowledge/conocimiento.pdf.
Requiere que la migracion supabase/migrations/0002_pgvector_documentos.sql
ya este aplicada en el proyecto Supabase.

El chunking se hace por pagina (no sobre el texto completo unido) para poder
citar la pagina de origen de cada chunk en las respuestas del agente.
"""

import sys
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.config import load_settings
from app.db.client import get_supabase_client

EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
DEFAULT_PDF_PATH = Path(__file__).parent / "conocimiento.pdf"


def extract_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def build_chunks(pages: list[str]) -> list[dict]:
    """Trocea cada pagina por separado, conservando el numero de pagina (1-indexed)."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = []
    for page_number, page_text in enumerate(pages, start=1):
        if not page_text.strip():
            continue
        for chunk_text in splitter.split_text(page_text):
            if chunk_text.strip():
                chunks.append({"content": chunk_text, "page": page_number})
    return chunks


def ingest(pdf_path: Path) -> int:
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo de conocimiento: {pdf_path}"
        )

    settings = load_settings()
    pages = extract_pages(pdf_path)
    chunks = build_chunks(pages)
    if not chunks:
        raise ValueError(f"No se extrajo texto util de {pdf_path}")

    embeddings_client = OpenAIEmbeddings(
        model=EMBEDDING_MODEL, api_key=settings.openai_api_key
    )
    vectors = embeddings_client.embed_documents([c["content"] for c in chunks])

    rows = [
        {
            "content": chunk["content"],
            "metadata": {
                "source": pdf_path.name,
                "page": chunk["page"],
                "chunk_index": i,
            },
            "embedding": vector,
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]

    client = get_supabase_client()
    client.table("documentos").insert(rows).execute()
    return len(rows)


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF_PATH
    inserted = ingest(pdf_path)
    print(f"Ingesta completa: {inserted} chunks insertados desde {pdf_path}")


if __name__ == "__main__":
    main()
