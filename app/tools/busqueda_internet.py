from langchain.tools import tool
from tavily import TavilyClient

from app.config import load_settings
from app.resilience import with_retry

DEFAULT_MAX_RESULTS = 5


@tool
@with_retry
def busqueda_internet(consulta: str) -> str:
    """Realiza una busqueda en Internet (via Tavily) para responder preguntas sobre
    informacion externa/actual que no esta en la base de conocimiento interna.
    Esta tool solo se expone al agente cuando el usuario pide explicitamente
    'busca en internet' en su mensaje.
    """
    settings = load_settings()
    if not settings.tavily_api_key:
        return (
            "La tool de busqueda en Internet todavia no esta configurada "
            "(falta TAVILY_API_KEY en .env)."
        )

    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(query=consulta, max_results=DEFAULT_MAX_RESULTS)

    resultados = response.get("results", [])
    if not resultados:
        return "No se encontraron resultados en Internet para esa consulta."

    return "\n\n---\n\n".join(
        f"{r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}"
        for r in resultados
    )
