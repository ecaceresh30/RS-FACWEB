from langchain_openai import ChatOpenAI

from app.config import load_settings

# Techo de seguridad, no un limite de estilo: el system prompt ya le pide al
# modelo ser conciso, pero eso es una sugerencia, no una garantia. Sin esto, un
# prompt muy generalista puede disparar una respuesta arbitrariamente larga,
# afectando latencia/costo y, con el indicador de fase (ver app/conversation.py),
# dejando al usuario esperando sin feedback incremental. 2000 tokens (~1500
# palabras) es generoso a proposito: las respuestas reales del agente sobre el
# manual (incluso con listas de varios pasos) rondan unos cientos de tokens, asi
# que este limite no deberia truncar una respuesta legitima, solo actuar como
# salvavidas ante el caso patologico.
MAX_OUTPUT_TOKENS = 2000


def get_llm() -> ChatOpenAI:
    settings = load_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
