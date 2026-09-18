"""Genera app/knowledge/recomendaciones_cartera.pdf: contenido educativo sobre
gestion de cartera de cuentas por cobrar, factoring/factura negociable y
alternativas de financiamiento en Peru.

Contenido verificado con busqueda web (no inventado) al momento de escribirlo:
- Las 11 cajas municipales supervisadas por la SBS y respaldadas por el Fondo
  de Seguro de Depositos.
- Bancos y fintechs que ofrecen factoring en Peru, y cifras de mercado de la
  factura negociable.
Los nombres de entidades son reales; las tasas y condiciones especificas NO se
incluyen porque cambian con frecuencia y no se pueden verificar en tiempo real
- el texto remite a SBS y a cada entidad para eso.

Uso: python -m app.knowledge.generar_recomendaciones_cartera
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT_PATH = Path(__file__).parent / "recomendaciones_cartera.pdf"

SECCIONES = [
    (
        "1. Que es la cartera de cuentas por cobrar",
        "La cartera de cuentas por cobrar es el conjunto de facturas y boletas que una "
        "empresa ha emitido a credito a sus clientes y que aun no han sido cobradas. "
        "Gestionarla bien es tan importante como generar ventas: una empresa puede ser "
        "rentable en el papel y aun asi quedarse sin liquidez si sus clientes tardan "
        "demasiado en pagar.\n\n"
        "Dos conceptos centrales para evaluar la salud de una cartera:\n"
        "- Antiguedad de saldos (aging): clasificar cada factura pendiente segun cuantos "
        "dias lleva vencida (vigente, 1-30, 31-60, 61-90, mas de 90 dias).\n"
        "- Concentracion: que porcentaje de la cartera total depende de uno o pocos "
        "clientes. Alta concentracion es un riesgo si ese cliente atrasa sus pagos."
    ),
    (
        "2. Senales de alerta en una cartera",
        "Algunas senales de que una cartera necesita atencion:\n"
        "- Crecimiento sostenido del monto en los tramos de mora mas altos (61-90, 90+).\n"
        "- Clientes recurrentes que siempre pagan tarde, sin que cambien las condiciones "
        "de credito que se les otorgan.\n"
        "- Dependencia de pocos clientes para una porcion grande del monto por cobrar.\n"
        "- Necesidad frecuente de capital de trabajo pese a tener ventas saludables: "
        "sintoma de que el dinero esta 'atrapado' en facturas por cobrar.\n\n"
        "Cuando aparecen estas senales, dos caminos complementarios ayudan: mejorar las "
        "practicas de cobranza (seccion 6) y/o convertir cuentas por cobrar en liquidez "
        "inmediata mediante factoring (siguiente seccion)."
    ),
    (
        "3. Que es el factoring y la factura negociable en Peru",
        "El factoring es un mecanismo de financiamiento donde una empresa vende sus "
        "facturas por cobrar (a credito) a un tercero (banco, financiera o empresa de "
        "factoring) a cambio de un adelanto de efectivo, descontando una comision/tasa "
        "por el adelanto y por el riesgo asumido. En Peru, el instrumento legal que "
        "permite hacer esto es la 'factura negociable', regulada por la Ley N.o 29623 y "
        "sus modificatorias.\n\n"
        "El mercado de facturas negociables esta en crecimiento sostenido: segun el "
        "Diario Oficial El Peruano, al cierre del primer semestre de 2026 el monto "
        "negociado alcanzo S/ 27,019 millones, un crecimiento de 14.6% respecto al mismo "
        "periodo de 2025, y el 84.5% de las empresas que usan este mecanismo son MYPE - "
        "es decir, no es una herramienta exclusiva de grandes empresas.\n\n"
        "La Superintendencia de Banca, Seguros y AFP (SBS) supervisa a los bancos, "
        "financieras y cajas que operan en el sistema financiero peruano, y mantiene un "
        "registro de empresas de factoring (comprendidas y no comprendidas en la Ley "
        "General) en www.sbs.gob.pe."
    ),
    (
        "4. Como elegir un proveedor de factoring",
        "Antes de elegir con quien hacer factoring, comparar al menos:\n"
        "- Tasa de descuento efectiva (no solo la tasa nominal) y todas las comisiones "
        "asociadas (estructuracion, custodia, etc.).\n"
        "- Porcentaje de adelanto sobre el valor de la factura (rara vez es el 100%).\n"
        "- Si es factoring 'con recurso' (si el cliente final no paga, la empresa que "
        "vendio la factura responde) o 'sin recurso' (el riesgo de no pago lo asume "
        "quien compra la factura) - el segundo suele costar mas pero traslada el riesgo.\n"
        "- Plazo de desembolso: cuanto tarda en llegar el dinero luego de aprobar la "
        "operacion.\n"
        "- Si la entidad esta supervisada por la SBS o registrada como empresa de "
        "factoring - verificable directamente en www.sbs.gob.pe.\n\n"
        "Ninguna cifra de tasas o plazos se incluye en este documento porque cambian con "
        "frecuencia; se debe solicitar una cotizacion vigente directamente a cada entidad."
    ),
    (
        "5. Bancos que ofrecen factoring en Peru",
        "Varios de los principales bancos del pais ofrecen productos de factoring para "
        "proveedores, entre ellos:\n"
        "- Banco de Credito del Peru (BCP): 'Adelanto en Linea', con opciones flexibles "
        "de seleccion de facturas a adelantar.\n"
        "- Interbank: 'Factoring Electronico Proveedores', con modalidades con y sin "
        "confirmacion del cliente final.\n"
        "- Scotiabank: 'Factoring para Proveedores', financiamiento de facturas en el "
        "corto plazo.\n\n"
        "Estos son productos bancarios tradicionales de factoring; conviene consultar "
        "directamente con cada banco las condiciones vigentes y si la empresa califica."
    ),
    (
        "6. Empresas de factoring especializadas (fintech) en Peru",
        "Ademas de los bancos, operan en Peru empresas y plataformas especializadas en "
        "factoring / factura negociable, entre ellas: Facturedo Peru, Finsmart Peru, "
        "Peru Factoring, Optima Factoring Peru, Logros Factoring Peru, Adelanta "
        "Factoring y Prestamype Factoring. Varias funcionan como marketplace, conectando "
        "empresas que necesitan capital de trabajo con inversionistas que compran las "
        "facturas.\n\n"
        "Antes de operar con cualquiera de estas empresas, verificar su registro vigente "
        "en la SBS (seccion de empresas de factoring, comprendidas o no en la Ley "
        "General) y comparar condiciones segun los criterios de la seccion 4."
    ),
    (
        "7. Cajas municipales: alternativa de credito de capital de trabajo",
        "El factoring no es la unica salida si una empresa necesita liquidez por una "
        "cartera con mora: tambien puede evaluar un credito de capital de trabajo. Las "
        "cajas municipales de ahorro y credito son una alternativa relevante para "
        "MYPE, especialmente fuera de Lima. Peru tiene 11 cajas municipales, todas "
        "supervisadas por la SBS y con depositos respaldados por el Fondo de Seguro de "
        "Depositos (FSD):\n\n"
        "Caja Arequipa, Caja Cusco, Caja Del Santa, Caja Huancayo, Caja Ica, Caja "
        "Maynas, Caja Paita, Caja Piura, Caja Sullana, Caja Tacna y Caja Trujillo.\n\n"
        "Un credito de capital de trabajo (a diferencia del factoring) no vende las "
        "facturas: es un prestamo que la empresa debe devolver segun un cronograma, "
        "usando su cartera y flujo de caja como parte del sustento para calificar. "
        "Comparar tasa efectiva anual, plazo y garantias exigidas entre varias cajas "
        "antes de decidir, y verificar la vigencia de cada entidad en www.sbs.gob.pe."
    ),
    (
        "8. Buenas practicas de cobranza para reducir la mora",
        "Medidas preventivas y de seguimiento que reducen la mora sin necesidad de "
        "financiamiento externo:\n"
        "- Definir una politica de credito clara (a quien se le da credito, por cuanto "
        "monto y plazo) antes de otorgarlo, no despues de que hay problemas.\n"
        "- Enviar recordatorios de pago antes del vencimiento, no solo despues.\n"
        "- Escalar la gestion de cobranza segun el tramo de mora: un recordatorio "
        "amistoso a los pocos dias de vencido, contacto directo mas firme en 31-60 dias, "
        "y evaluar acciones formales (conciliacion, cobranza judicial) pasados los 90 "
        "dias segun el monto involucrado.\n"
        "- Diversificar la base de clientes para no depender de uno o dos clientes "
        "grandes que concentren la mayoria del riesgo de cartera.\n"
        "- Revisar periodicamente el limite de credito otorgado a clientes con "
        "historial de pagos tardios."
    ),
    (
        "9. Nota importante",
        "Este documento tiene fines educativos e informativos generales. No constituye "
        "asesoria financiera personalizada. Los nombres de bancos, cajas municipales y "
        "empresas de factoring mencionados son reales y estaban vigentes al momento de "
        "elaborar este documento, pero las tasas, comisiones, plazos y condiciones "
        "especificas cambian con frecuencia y deben verificarse directamente con cada "
        "entidad y/o en el portal oficial de la Superintendencia de Banca, Seguros y AFP "
        "(www.sbs.gob.pe) antes de tomar una decision."
    ),
]


def build_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_title("Recomendaciones para carteras con deudas: factoring y cobranza")

    for titulo, cuerpo in SECCIONES:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, titulo.encode("latin-1", "replace").decode("latin-1"))
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, cuerpo.encode("latin-1", "replace").decode("latin-1"))

    return pdf


def main() -> None:
    pdf = build_pdf()
    pdf.output(str(OUTPUT_PATH))
    print(f"PDF generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
