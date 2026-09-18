from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings

from app.config import load_settings
from app.db.client import get_supabase_client
from app.knowledge.ingest import EMBEDDING_MODEL
from app.resilience import with_retry

DEFAULT_MATCH_COUNT = 5

# Se piden mas candidatos de los que finalmente se usan (DEFAULT_MATCH_COUNT) para
# poder aislar despues el `source` dominante entre varios documentos en la misma
# tabla `documentos` (ver mas abajo) sin perder cobertura dentro de ese documento.
CANDIDATE_POOL_COUNT = 10

# Similitud coseno minima para considerar un chunk relevante. Calibrado con datos
# reales: charla casual ("hola", "cuentame un chiste") puntua ~0.22-0.30, preguntas
# de dominio sobre el manual puntuan ~0.54-0.66. 0.40 separa ambos casos con margen.
MIN_SIMILARITY = 0.40


@with_retry
def retrieve_context(consulta: str) -> tuple[str, list[dict]]:
    """Recupera los chunks relevantes de la base de conocimiento para `consulta`.

    Devuelve (contexto, fuentes). `contexto` es "" y `fuentes` es [] si no hay
    matches por encima de MIN_SIMILARITY (ej. charla casual sin relacion con el
    manual). Esta funcion es la que usa app/main.py para inyectar contexto y citar
    la fuente de forma determinista en cada turno (no depende del criterio del LLM
    para decidir si buscar o no).

    Cuando hay varios documentos en `documentos` (ej. conocimiento.pdf +
    conocimiento_sire.pdf), el resultado se restringe al `source` del match con
    mayor similitud, descartando matches de otros documentos aunque superen
    MIN_SIMILARITY. Verificado en vivo: ambos manuales comparten vocabulario
    tecnico generico ("manejo de errores", "codigo de error") que sin este filtro
    hace que preguntas sobre un documento traigan chunks del otro que describen un
    procedimiento distinto (ej. codigos de rechazo de comprobantes mezclados en una
    respuesta sobre diferencias de SIRE).
    """
    settings = load_settings()
    embeddings_client = OpenAIEmbeddings(
        model=EMBEDDING_MODEL, api_key=settings.openai_api_key
    )
    query_embedding = embeddings_client.embed_query(consulta)

    client = get_supabase_client()
    response = client.rpc(
        "match_documents",
        {"query_embedding": query_embedding, "match_count": CANDIDATE_POOL_COUNT},
    ).execute()

    matches = [m for m in response.data if m.get("similarity", 0) >= MIN_SIMILARITY]
    if not matches:
        return "", []

    top_source = matches[0].get("metadata", {}).get("source")
    matches = [m for m in matches if m.get("metadata", {}).get("source") == top_source]
    matches = matches[:DEFAULT_MATCH_COUNT]

    contexto = "\n\n---\n\n".join(m["content"] for m in matches)
    fuentes = [
        {
            "source": m.get("metadata", {}).get("source"),
            "page": m.get("metadata", {}).get("page"),
        }
        for m in matches
    ]
    return contexto, fuentes


@tool
def buscar_conocimiento(consulta: str) -> str:
    """Busca informacion relevante en la base de conocimiento interna (conocimiento.pdf)
    usando busqueda semantica sobre los embeddings almacenados en Supabase/pgvector.
    Usar esta tool para responder preguntas sobre el contenido documentado del negocio.
    """
    contexto, _fuentes = retrieve_context(consulta)
    if not contexto:
        return "No se encontro informacion relevante en la base de conocimiento."
    return contexto
