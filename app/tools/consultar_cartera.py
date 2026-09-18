"""Consulta de la cartera de cuentas por cobrar del usuario logueado.

Gatillada por una frase fija ("cartera" en el mensaje), igual que
busqueda_internet y el comando de RUC - no depende del criterio del LLM para
decidir si consultar o no. Devuelve un resumen textual determinista de hechos
(montos, tramos de mora); el analisis, la interpretacion y la recomendacion de
factoring/financiamiento las hace el LLM sobre estos hechos y sobre el contexto
de la base de conocimiento (ver app/conversation.py y app/agent/agent.py).
"""

import re

from app.db import cartera_repository
from app.resilience import with_retry
from app.tools.buscar_conocimiento import retrieve_full_document

CARTERA_TRIGGER = "cartera"
RECOMENDACIONES_PDF = "recomendaciones_cartera.pdf"

TRAMOS_ORDEN = ("vigente", "1-30", "31-60", "61-90", "90+")

MAX_PREGUNTAS_SUGERIDAS = 3

# Palabras clave que indican que el usuario pide una recomendacion/evaluacion de
# su cartera (factoring, financiamiento), no solo un dato puntual. Deben cubrir
# los mismos ejemplos que el system prompt (ver app/agent/agent.py) usa para
# decidir si el LLM puede analizar/recomendar: mismo criterio determinista en
# ambos lados. Se usa tanto para decidir si traer el PDF de recomendaciones
# (obtener_contexto_recomendaciones) como para no repetir esa categoria en las
# preguntas sugeridas.
RECOMENDACION_KEYWORDS: tuple[str, ...] = (
    "recomien",
    "conviene",
    "financia",
    "factoring",
    "liquidez",
    "caja",
    "opcion",
    "opción",
    "evalua",
    "evalúa",
    "deberia",
    "debería",
    "debo",
)

# Categorias de preguntas sobre cartera. Cada una trae sus palabras clave (para
# no repetir una categoria que el usuario ya toco en su mensaje) y la pregunta
# sugerida asociada. Todas incluyen la palabra "cartera" a proposito: si el
# usuario hace click y la reenvia tal cual, debe volver a activar
# wants_cartera_consulta (mismo gatillo determinista de siempre).
CATEGORIAS_SUGERENCIAS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "monto",
        ("monto", "total", "cuanto", "cuánto", "asciende", "suma"),
        "¿A cuánto asciende el monto total pendiente de cobro en mi cartera?",
    ),
    (
        "tramos",
        ("tramo", "mora", "vencimiento", "antiguedad", "antigüedad"),
        "¿Cómo se distribuye mi cartera por tramo de mora?",
    ),
    (
        "facturas_vencidas",
        # "cliente" se sacó de esta lista: es una palabra generica de negocio
        # (aparece en marketing/ventas/CRM) que no tiene nada que ver con
        # cuentas por cobrar - matcheaba "cartera de clientes potenciales" en
        # una pregunta de marketing y filtraba deuda real con nombre y monto
        # (ver hallazgo de pruebas, docs/informe.txt). "factura"/"vencid" son
        # especificas de este dominio y no tienen ese problema.
        ("factura", "vencid"),
        "¿Cuáles son las facturas más vencidas de mi cartera?",
    ),
    (
        "recomendacion",
        RECOMENDACION_KEYWORDS,
        "¿Qué recomendaciones de factoring o financiamiento tienes para mi cartera?",
    ),
)

CATEGORIA_KEYWORDS: dict[str, tuple[str, ...]] = {
    categoria: palabras_clave for categoria, palabras_clave, _ in CATEGORIAS_SUGERENCIAS
}


def wants_cartera_consulta(user_input: str) -> bool:
    return CARTERA_TRIGGER in user_input.lower()


def _contiene_alguna_palabra(mensaje: str, palabras: tuple[str, ...]) -> bool:
    """Como `any(p in mensaje for p in palabras)` pero exige limite de palabra a
    la izquierda, para que stems cortos como "caja" u "opcion" no matcheen
    dentro de otra palabra (ej. "encaja", "adopcion")."""
    return any(re.search(rf"\b{re.escape(palabra)}", mensaje) for palabra in palabras)


def wants_recomendacion_cartera(user_input: str) -> bool:
    """True si el usuario pide explicitamente una recomendacion/evaluacion de su
    cartera (no solo un dato puntual como el monto o los tramos de mora)."""
    return _contiene_alguna_palabra(user_input.lower(), RECOMENDACION_KEYWORDS)


def sugerir_preguntas_cartera(user_input: str) -> list[str]:
    """Hasta MAX_PREGUNTAS_SUGERIDAS preguntas de seguimiento sobre cartera,
    relacionadas con la pregunta principal del usuario: se excluyen las
    categorias que el mensaje ya toco, para no repetir lo que ya se respondio.
    Deterministico (sin LLM), consistente con el resto del gating de esta tool."""
    mensaje = user_input.lower()
    candidatas = [
        pregunta
        for _categoria, palabras_clave, pregunta in CATEGORIAS_SUGERENCIAS
        if not _contiene_alguna_palabra(mensaje, palabras_clave)
    ]
    return candidatas[:MAX_PREGUNTAS_SUGERIDAS]


def obtener_contexto_recomendaciones() -> tuple[str, list[dict]]:
    """Contenido completo del PDF de recomendaciones de factoring/cobranza
    (9 paginas, corto) - ver retrieve_full_document para el porque de no usar
    el top-K generico aqui."""
    return retrieve_full_document(RECOMENDACIONES_PDF)


def _agregar_cartera(filas: list[dict]) -> dict:
    """Agrega las filas crudas de cartera (montos, tramos, facturas vencidas).
    Logica compartida entre obtener_resumen_cartera (texto plano para el
    contexto del LLM) y obtener_tabla_cartera (datos estructurados para la
    tabla responsive del frontend), para no calcularla dos veces."""
    total_pendiente = sum(f["monto_pendiente"] for f in filas)
    por_tramo: dict[str, dict[str, float]] = {}
    for f in filas:
        tramo = f["tramo_mora"]
        acumulado = por_tramo.setdefault(tramo, {"cantidad": 0, "monto": 0.0})
        acumulado["cantidad"] += 1
        acumulado["monto"] += float(f["monto_pendiente"])

    vencidas = sorted(
        (f for f in filas if f["tramo_mora"] != "vigente"),
        key=lambda f: f["dias_vencido"],
        reverse=True,
    )[:10]

    return {
        "total_facturas": len(filas),
        "monto_total": total_pendiente,
        "por_tramo": por_tramo,
        "vencidas": vencidas,
    }


@with_retry
def obtener_resumen_cartera(emisor_ruc: str) -> str:
    """Devuelve "" si el usuario no tiene cartera registrada."""
    filas = cartera_repository.get_cartera(emisor_ruc)
    if not filas:
        return ""

    agregado = _agregar_cartera(filas)
    por_tramo = agregado["por_tramo"]

    lineas = [
        f"{agregado['total_facturas']} facturas a credito en soles (PEN).",
        f"Monto total pendiente de cobro: S/ {agregado['monto_total']:,.2f}",
        "Distribucion por tramo de mora:",
    ]
    for tramo in TRAMOS_ORDEN:
        datos = por_tramo.get(tramo)
        if datos:
            lineas.append(
                f"- {tramo}: {int(datos['cantidad'])} facturas, S/ {datos['monto']:,.2f}"
            )

    if agregado["vencidas"]:
        lineas.append("Facturas vencidas con mayor antiguedad:")
        for f in agregado["vencidas"]:
            factura = f["facturas"]
            lineas.append(
                f"- {factura['numero']} ({factura['cliente_nombre']}): "
                f"S/ {float(f['monto_pendiente']):,.2f}, {f['dias_vencido']} dias vencido"
            )

    return "\n".join(lineas)


@with_retry
def obtener_tabla_cartera(emisor_ruc: str) -> dict | None:
    """Igual que obtener_resumen_cartera pero en formato estructurado (JSON),
    para que el frontend renderice una tabla responsive con los montos
    alineados a la derecha en vez de depender de que el LLM la formatee bien
    en texto. None si no hay cartera registrada."""
    filas = cartera_repository.get_cartera(emisor_ruc)
    if not filas:
        return None

    agregado = _agregar_cartera(filas)
    por_tramo = agregado["por_tramo"]

    tramos = [
        {
            "tramo": tramo,
            "cantidad": int(por_tramo[tramo]["cantidad"]),
            "monto": round(por_tramo[tramo]["monto"], 2),
        }
        for tramo in TRAMOS_ORDEN
        if tramo in por_tramo
    ]
    facturas_vencidas = [
        {
            "numero": f["facturas"]["numero"],
            "cliente": f["facturas"]["cliente_nombre"],
            "monto": round(float(f["monto_pendiente"]), 2),
            "dias_vencido": f["dias_vencido"],
        }
        for f in agregado["vencidas"]
    ]
    return {
        "total_facturas": agregado["total_facturas"],
        "monto_total": round(agregado["monto_total"], 2),
        "tramos": tramos,
        "facturas_vencidas": facturas_vencidas,
    }


def seleccionar_tabla_cartera(tabla: dict | None, user_input: str) -> dict | None:
    """Recorta `tabla` a solo las listas (tramos, facturas vencidas) que el
    usuario realmente pidio, usando las mismas categorias/palabras clave que
    sugerir_preguntas_cartera. Una pregunta puntual (ej. "a cuanto asciende el
    monto total") o un pedido de recomendacion/evaluacion (ej. "que me
    recomiendas") no deben traer tabla: la respuesta es una cifra o un analisis
    en prosa, no una lista. Si la pregunta es completamente abierta (no
    menciona ninguna categoria puntual) se devuelve el agregado por tramo,
    pero NO el detalle nominal de facturas/clientes (mas sensible: nombres de
    clientes y montos de deuda) salvo que se pida explicitamente: el gate de
    "cartera" es literal (substring), y "cartera"/"cliente" pueden aparecer en
    una pregunta que no tiene nada que ver con cuentas por cobrar (ej.
    "cartera de clientes potenciales" en una pregunta de marketing) - en ese
    caso no corresponde filtrar deuda real de clientes con nombre y apellido.
    None si no hay nada que mostrar en tabla."""
    if not tabla:
        return None

    mensaje = user_input.lower()
    pide_monto = _contiene_alguna_palabra(mensaje, CATEGORIA_KEYWORDS["monto"])
    pide_tramos = _contiene_alguna_palabra(mensaje, CATEGORIA_KEYWORDS["tramos"])
    pide_vencidas = _contiene_alguna_palabra(mensaje, CATEGORIA_KEYWORDS["facturas_vencidas"])
    pide_recomendacion = _contiene_alguna_palabra(mensaje, CATEGORIA_KEYWORDS["recomendacion"])

    if not pide_monto and not pide_tramos and not pide_vencidas and not pide_recomendacion:
        return {**tabla, "facturas_vencidas": []}

    seleccion = {
        **tabla,
        "tramos": tabla["tramos"] if pide_tramos else [],
        "facturas_vencidas": tabla["facturas_vencidas"] if pide_vencidas else [],
    }
    if not seleccion["tramos"] and not seleccion["facturas_vencidas"]:
        return None
    return seleccion
