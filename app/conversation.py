"""Logica de sesion y turno compartida entre el CLI (app/main.py) y la API web
(app/api.py): login/registro por RUC, RAG con cita determinista, comando de
busqueda de otro RUC, y persistencia en Supabase.

Se centraliza aqui para que ambas interfaces (CLI y web) se comporten
identico y no se dupliquen bugs como el de la cita "Fuente" filtrandose al
historial que ve el LLM.
"""

import re
from dataclasses import dataclass, field

from app.agent.agent import build_agent, wants_internet_search
from app.db import conversation_repository, message_repository, user_repository
from app.tools.buscar_conocimiento import retrieve_context
from app.tools.consultar_api_externa import consultar_ruc
from app.tools.consultar_cartera import (
    obtener_contexto_recomendaciones,
    obtener_resumen_cartera,
    wants_cartera_consulta,
)

RUC_PATTERN = re.compile(r"^\d{11}$")
RUC_SEARCH_PATTERN = re.compile(r"busca\s+(?:al\s+|el\s+)?ruc\s+(\d{11})", re.IGNORECASE)
FUENTE_SUFFIX_PATTERN = re.compile(r"\n\nFuente:.*$", re.DOTALL)


class RucInvalidoError(Exception):
    """El RUC no tiene el formato esperado (11 digitos numericos)."""


class RucNoEncontradoError(Exception):
    """OpenRuc no encontro el RUC (no existe o esta fuera de su alcance)."""


class TurnoError(Exception):
    """Fallo no recuperable al procesar un turno (ya se reintento via with_retry)."""


@dataclass
class Sesion:
    usuario: dict
    conversacion: dict
    messages: list[dict]
    es_nuevo: bool
    agent_sin_internet: object
    agent_con_internet: object


@dataclass
class ResultadoTurno:
    respuesta: str
    avisos: list[str] = field(default_factory=list)


def _strip_fuente_suffix(content: str) -> str:
    """Quita el sufijo '\\n\\nFuente: ...' antes de re-enviar un turno como
    historial al LLM. Si no se limpia, el modelo ve sus propias respuestas
    pasadas terminando en 'Fuente: ...' y empieza a imitar/alucinar ese patron
    en respuestas nuevas (la cita real se vuelve a anexar de forma determinista
    despues de cada invocacion, no debe ser parte de lo que el LLM "recuerda"
    haber dicho)."""
    return FUENTE_SUFFIX_PATTERN.sub("", content)


def cargar_historial(conversacion_id: str) -> list[dict]:
    return [
        {
            "role": m["role"],
            "content": (
                _strip_fuente_suffix(m["content"]) if m["role"] == "assistant" else m["content"]
            ),
        }
        for m in message_repository.get_messages(conversacion_id)
    ]


def _build_augmented_user_message(
    user_input: str, contexto: str, resumen_cartera: str = ""
) -> dict:
    """Inyecta el contexto recuperado de la base de conocimiento (y, si aplica,
    el resumen de cartera) en el turno actual.

    Solo se usa para la invocacion al agente (no se persiste ni se guarda en el
    historial en memoria) para que el prompt del sistema pueda exigir exclusividad
    sobre ese contexto en la respuesta.
    """
    bloque_contexto = contexto or "(sin resultados relevantes en la base de conocimiento)"
    content = (
        f"{user_input}\n\n---\n"
        "Contexto recuperado de la base de conocimiento interna "
        "(puede no ser relevante si el mensaje es charla casual):\n"
        f"{bloque_contexto}"
    )
    if resumen_cartera:
        content += f"\n\n---\nDatos de tu cartera de cuentas por cobrar:\n{resumen_cartera}"
    return {"role": "user", "content": content}


def _format_sources(fuentes: list[dict]) -> str:
    paginas_por_fuente: dict[str, list] = {}
    for f in fuentes:
        paginas = paginas_por_fuente.setdefault(f["source"], [])
        page = f.get("page")
        if page is not None and page not in paginas:
            paginas.append(page)

    partes = [
        f"{source}, pag. {','.join(str(p) for p in paginas)}" if paginas else source
        for source, paginas in paginas_por_fuente.items()
    ]
    return "Fuente: " + "; ".join(partes)


def _format_empresa_info(datos: dict) -> str:
    return (
        f"RUC: {datos.get('ruc')}\n"
        f"Razon social: {datos.get('razon_social')}\n"
        f"Estado: {datos.get('estado')}\n"
        f"Condicion: {datos.get('condicion')}\n"
        f"Direccion: {datos.get('direccion')}\n"
        f"Ubigeo: {datos.get('ubigeo')}"
    )


def _resolve_conversacion(usuario: dict, es_nuevo: bool) -> dict:
    if es_nuevo:
        return conversation_repository.create_conversation(usuario["ruc"])

    conversacion = conversation_repository.get_latest_conversation(usuario["ruc"])
    if conversacion is None:
        conversacion = conversation_repository.create_conversation(usuario["ruc"])
    return conversacion


def iniciar_sesion(ruc: str) -> Sesion:
    """Login/registro por RUC. Si el RUC no existe en Supabase, lo consulta en
    OpenRuc y lo cachea. Lanza RucInvalidoError / RucNoEncontradoError en los
    casos correspondientes."""
    if not RUC_PATTERN.fullmatch(ruc):
        raise RucInvalidoError("El RUC debe tener exactamente 11 digitos numericos.")

    usuario = user_repository.get_by_ruc(ruc)
    es_nuevo = usuario is None
    if es_nuevo:
        datos = consultar_ruc(ruc)
        if datos is None:
            raise RucNoEncontradoError(f"No se encontro el RUC {ruc} en SUNAT (via OpenRuc).")
        usuario = user_repository.create(datos)

    conversacion = _resolve_conversacion(usuario, es_nuevo)
    messages = cargar_historial(conversacion["id"])
    agent_sin_internet = build_agent(include_busqueda_internet=False, usuario=usuario)
    agent_con_internet = build_agent(include_busqueda_internet=True, usuario=usuario)

    return Sesion(
        usuario=usuario,
        conversacion=conversacion,
        messages=messages,
        es_nuevo=es_nuevo,
        agent_sin_internet=agent_sin_internet,
        agent_con_internet=agent_con_internet,
    )


def _fase_label(
    fuentes: list[dict], quiere_internet: bool, consulta_cartera: bool = False
) -> str:
    """Etiqueta determinista de que fuente se esta consultando, calculada con la
    misma informacion que ya se resuelve antes de invocar al LLM (fuentes de
    retrieve_context, gate de busqueda en internet, gate de consulta de
    cartera). La usa la API web como indicador de progreso mientras se espera
    la respuesta (ver app/api.py); no participa en ninguna decision del flujo,
    solo describe lo ya decidido."""
    fuentes_txt = []
    if consulta_cartera:
        fuentes_txt.append("tu cartera")
    fuentes_txt.extend(sorted({f["source"] for f in fuentes if f.get("source")}))
    combinado = " y ".join(fuentes_txt)

    if combinado and quiere_internet:
        return f"Consultando {combinado} y buscando en internet..."
    if combinado:
        return f"Consultando {combinado}..."
    if quiere_internet:
        return "Buscando en internet..."
    return "Generando respuesta..."


def _procesar_turno_gen(sesion: Sesion, user_input: str):
    """Generador interno compartido por procesar_turno (CLI, bloqueante) y
    procesar_turno_stream (API web, streaming). Muta sesion.messages in place
    (agrega el turno de usuario y la respuesta limpia, sin cita).

    Yields ('fase', texto) tan pronto se conoce la fuente que se va a consultar
    (antes de invocar al LLM) y al final ('resultado', ResultadoTurno) con el
    texto a mostrar (con cita si aplica) y avisos no fatales (fallos de
    persistencia)."""
    avisos: list[str] = []
    conversacion = sesion.conversacion
    messages = sesion.messages

    messages.append({"role": "user", "content": user_input})
    try:
        message_repository.add_message(conversacion["id"], "user", user_input)
    except Exception as exc:
        avisos.append(f"No se pudo guardar tu mensaje en el historial: {type(exc).__name__}")

    ruc_buscado = RUC_SEARCH_PATTERN.search(user_input)
    if ruc_buscado:
        yield ("fase", "Consultando OpenRuc...")
        try:
            datos = consultar_ruc(ruc_buscado.group(1))
        except Exception as exc:
            raise TurnoError(
                f"Hubo un problema temporal consultando OpenRuc ({type(exc).__name__})."
            ) from exc

        if datos is not None:
            respuesta_limpia = _format_empresa_info(datos)
            respuesta_mostrada = f"{respuesta_limpia}\n\nFuente: OpenRuc"
        else:
            respuesta_limpia = f"No se encontro informacion para el RUC {ruc_buscado.group(1)}."
            respuesta_mostrada = respuesta_limpia
    else:
        try:
            contexto, fuentes = retrieve_context(user_input)
        except Exception as exc:
            contexto, fuentes = "", []
            avisos.append(f"No se pudo consultar la base de conocimiento: {type(exc).__name__}")

        consulta_cartera = wants_cartera_consulta(user_input)
        resumen_cartera = ""
        if consulta_cartera:
            try:
                resumen_cartera = obtener_resumen_cartera(sesion.usuario["ruc"])
            except Exception as exc:
                avisos.append(f"No se pudo consultar tu cartera: {type(exc).__name__}")
            try:
                contexto_completo, fuentes_completo = obtener_contexto_recomendaciones()
                if contexto_completo:
                    contexto, fuentes = contexto_completo, fuentes_completo
            except Exception as exc:
                avisos.append(
                    f"No se pudo consultar las recomendaciones de cartera: {type(exc).__name__}"
                )

        quiere_internet = wants_internet_search(user_input)
        yield ("fase", _fase_label(fuentes, quiere_internet, consulta_cartera))

        invoke_messages = [
            *messages[:-1],
            _build_augmented_user_message(user_input, contexto, resumen_cartera),
        ]
        agent = sesion.agent_con_internet if quiere_internet else sesion.agent_sin_internet
        try:
            result = agent.invoke({"messages": invoke_messages})
            respuesta_limpia = result["messages"][-1].content
        except Exception as exc:
            raise TurnoError(
                f"Hubo un problema temporal procesando tu mensaje ({type(exc).__name__})."
            ) from exc

        respuesta_mostrada = (
            f"{respuesta_limpia}\n\n{_format_sources(fuentes)}" if fuentes else respuesta_limpia
        )

    messages.append({"role": "assistant", "content": respuesta_limpia})
    try:
        message_repository.add_message(conversacion["id"], "assistant", respuesta_mostrada)
        conversation_repository.touch_conversation(conversacion["id"])
    except Exception as exc:
        avisos.append(f"No se pudo guardar este turno en el historial: {type(exc).__name__}")

    yield ("resultado", ResultadoTurno(respuesta=respuesta_mostrada, avisos=avisos))


def procesar_turno(sesion: Sesion, user_input: str) -> ResultadoTurno:
    """Procesa un turno de conversacion de forma bloqueante (usado por el CLI).
    Ver _procesar_turno_gen para el detalle del flujo."""
    for tipo, payload in _procesar_turno_gen(sesion, user_input):
        if tipo == "resultado":
            return payload
    raise TurnoError("El procesamiento del turno no genero un resultado.")


def procesar_turno_stream(sesion: Sesion, user_input: str):
    """Generador publico para la API web: yields ('fase', texto) apenas se
    conoce la fuente a consultar, y luego ('resultado', ResultadoTurno). Permite
    mostrar un indicador de progreso real (no simulado) mientras se espera la
    respuesta del LLM. Ver _procesar_turno_gen."""
    yield from _procesar_turno_gen(sesion, user_input)
