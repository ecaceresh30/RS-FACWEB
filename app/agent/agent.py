from langchain.agents import create_agent

from app.agent.llm import get_llm
from app.tools.busqueda_internet import busqueda_internet

# El contexto de la base de conocimiento se inyecta de forma determinista en cada
# turno (ver app/main.py -> retrieve_context), no queda a criterio del LLM decidir
# si buscar o no. Por eso buscar_conocimiento ya no es una tool del agente: la
# recuperacion ya ocurrio antes de llegar aqui.
SYSTEM_PROMPT = (
    "Eres un asistente conversacional empresarial. Responde de forma clara y concisa.\n\n"
    "En cada turno recibiras, junto al mensaje del usuario, un bloque 'Contexto recuperado "
    "de la base de conocimiento interna'.\n"
    "- Si la pregunta es sobre procedimientos, politicas o informacion documentada del "
    "negocio: responde EXCLUSIVAMENTE con base en ese contexto. Si el contexto no contiene "
    "la respuesta, dilo explicitamente (ej. 'No tengo esa informacion en la base de "
    "conocimiento') en vez de completar con conocimiento general o inventar.\n"
    "- Si el mensaje es conversacion casual (saludos, agradecimientos, etc.) no relacionada "
    "con el negocio: ignora el contexto recuperado y responde con normalidad.\n\n"
    "Si ademas recibes un bloque 'Datos de tu cartera de cuentas por cobrar': responde "
    "primero, y solo, lo que el usuario pregunto (ej. si pide un monto o una cifra puntual, "
    "da esa cifra, sin agregar analisis ni recomendaciones no solicitadas).\n"
    "Agrega analisis de la salud de la cartera (tramos de mora, facturas vencidas) o "
    "sugerencias de factoring/financiamiento UNICAMENTE si el usuario lo pide de forma "
    "explicita en su mensaje (ej. 'que me recomiendas', 'me conviene', 'que deberia hacer', "
    "'opciones de financiamiento', 'evalua mi cartera'). Si no lo pide, no lo ofrezcas por tu "
    "cuenta. Cuando si lo pida, SOLO menciona entidades, criterios o cifras que esten "
    "presentes en el 'Contexto recuperado de la base de conocimiento interna' de ese mismo "
    "turno; si ese contexto no trae informacion de factoring/financiamiento, dilo "
    "explicitamente en vez de inventar nombres de empresas, tasas o condiciones.\n\n"
    "Si en cambio recibes un bloque indicando que el usuario pregunto por su cartera pero "
    "no tiene ninguna factura registrada: dile explicitamente que no tienes informacion de "
    "su cartera de cuentas por cobrar porque no tiene facturas registradas en el sistema. "
    "No analices salud de cartera, tramos de mora, ni ofrezcas recomendaciones de "
    "factoring/financiamiento en ese caso.\n\n"
    "IMPORTANTE: nunca escribas tu una linea 'Fuente: ...' en tu respuesta. La cita de la "
    "fuente se agrega automaticamente despues, fuera de tu control. Si ves 'Fuente: ...' al "
    "final de tus propios turnos anteriores en el historial, ignoralo: no es algo que tu "
    "hayas escrito, no lo repitas ni lo continues."
)

# busqueda_internet solo debe activarse cuando el usuario la pide explicitamente.
# La activacion es determinista (fuera del criterio del LLM): la tool ni siquiera
# se expone al agente salvo que el prompt contenga esta frase.
INTERNET_SEARCH_TRIGGER = "busca en internet"

# consultar_api_externa (OpenRuc) tampoco es una tool del agente: el comando
# "busca el ruc XXXXXXXXXXX" se maneja de forma determinista en app/main.py,
# igual que buscar_conocimiento.
BASE_TOOLS = []


def wants_internet_search(user_input: str) -> bool:
    return INTERNET_SEARCH_TRIGGER in user_input.lower()


def get_tools(include_busqueda_internet: bool) -> list:
    if include_busqueda_internet:
        return [*BASE_TOOLS, busqueda_internet]
    return list(BASE_TOOLS)


def build_system_prompt(usuario: dict | None) -> str:
    """Agrega los datos de la empresa logueada (cacheados de OpenRuc en `usuarios`)
    al prompt de sistema, para que el agente pueda responder preguntas sobre "mi
    informacion" (ej. "cual es mi ubigeo") sin inventar ni confundirlo con
    buscar_conocimiento (manual) o el comando de busqueda de otro RUC.
    """
    if usuario is None:
        return SYSTEM_PROMPT

    datos_usuario = (
        "\n\nDatos de la empresa actualmente logueada (no confundir con la base de "
        "conocimiento del negocio ni con la busqueda de otro RUC):\n"
        f"- RUC: {usuario.get('ruc')}\n"
        f"- Razon social: {usuario.get('razon_social')}\n"
        f"- Estado: {usuario.get('estado')}\n"
        f"- Condicion: {usuario.get('condicion')}\n"
        f"- Direccion: {usuario.get('direccion')}\n"
        f"- Ubigeo: {usuario.get('ubigeo')}\n\n"
        "Si el usuario pregunta por su propia informacion (ej. 'cual es mi ubigeo', "
        "'cual es mi direccion', 'cual es mi razon social', 'cual es mi RUC'), "
        "responde directamente con estos datos."
    )
    return SYSTEM_PROMPT + datos_usuario


def build_agent(include_busqueda_internet: bool = False, usuario: dict | None = None):
    return create_agent(
        model=get_llm(),
        tools=get_tools(include_busqueda_internet),
        system_prompt=build_system_prompt(usuario),
    )
