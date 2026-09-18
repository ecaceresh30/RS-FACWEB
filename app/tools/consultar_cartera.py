"""Consulta de la cartera de cuentas por cobrar del usuario logueado.

Gatillada por una frase fija ("cartera" en el mensaje), igual que
busqueda_internet y el comando de RUC - no depende del criterio del LLM para
decidir si consultar o no. Devuelve un resumen textual determinista de hechos
(montos, tramos de mora); el analisis, la interpretacion y la recomendacion de
factoring/financiamiento las hace el LLM sobre estos hechos y sobre el contexto
de la base de conocimiento (ver app/conversation.py y app/agent/agent.py).
"""

from app.db import cartera_repository
from app.resilience import with_retry
from app.tools.buscar_conocimiento import retrieve_full_document

CARTERA_TRIGGER = "cartera"
RECOMENDACIONES_PDF = "recomendaciones_cartera.pdf"

TRAMOS_ORDEN = ("vigente", "1-30", "31-60", "61-90", "90+")

MAX_PREGUNTAS_SUGERIDAS = 3

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
        ("factura", "vencid", "cliente"),
        "¿Cuáles son las facturas más vencidas de mi cartera?",
    ),
    (
        "recomendacion",
        ("recomien", "conviene", "financia", "factoring", "liquidez", "caja", "opcion", "opción"),
        "¿Qué recomendaciones de factoring o financiamiento tienes para mi cartera?",
    ),
)


def wants_cartera_consulta(user_input: str) -> bool:
    return CARTERA_TRIGGER in user_input.lower()


def sugerir_preguntas_cartera(user_input: str) -> list[str]:
    """Hasta MAX_PREGUNTAS_SUGERIDAS preguntas de seguimiento sobre cartera,
    relacionadas con la pregunta principal del usuario: se excluyen las
    categorias que el mensaje ya toco, para no repetir lo que ya se respondio.
    Deterministico (sin LLM), consistente con el resto del gating de esta tool."""
    mensaje = user_input.lower()
    candidatas = [
        pregunta
        for _categoria, palabras_clave, pregunta in CATEGORIAS_SUGERENCIAS
        if not any(palabra in mensaje for palabra in palabras_clave)
    ]
    return candidatas[:MAX_PREGUNTAS_SUGERIDAS]


def obtener_contexto_recomendaciones() -> tuple[str, list[dict]]:
    """Contenido completo del PDF de recomendaciones de factoring/cobranza
    (9 paginas, corto) - ver retrieve_full_document para el porque de no usar
    el top-K generico aqui."""
    return retrieve_full_document(RECOMENDACIONES_PDF)


@with_retry
def obtener_resumen_cartera(emisor_ruc: str) -> str:
    """Devuelve "" si el usuario no tiene cartera registrada."""
    filas = cartera_repository.get_cartera(emisor_ruc)
    if not filas:
        return ""

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

    lineas = [
        f"{len(filas)} facturas a credito en soles (PEN).",
        f"Monto total pendiente de cobro: S/ {total_pendiente:,.2f}",
        "Distribucion por tramo de mora:",
    ]
    for tramo in TRAMOS_ORDEN:
        datos = por_tramo.get(tramo)
        if datos:
            lineas.append(
                f"- {tramo}: {int(datos['cantidad'])} facturas, S/ {datos['monto']:,.2f}"
            )

    if vencidas:
        lineas.append("Facturas vencidas con mayor antiguedad:")
        for f in vencidas:
            factura = f["facturas"]
            lineas.append(
                f"- {factura['numero']} ({factura['cliente_nombre']}): "
                f"S/ {float(f['monto_pendiente']):,.2f}, {f['dias_vencido']} dias vencido"
            )

    return "\n".join(lineas)
