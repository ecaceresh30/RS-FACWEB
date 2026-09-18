"""Genera y siembra ~100 facturas a credito (en soles) simuladas en Supabase
(facturas + factura_detalle + cartera) para poder probar consultar_cartera de
punta a punta. Datos ficticios (nombres de clientes inventados) - no
representan operaciones reales.

Requiere que la migracion supabase/migrations/0003_cartera.sql ya este
aplicada, y que el RUC exista o pueda registrarse via OpenRuc.

Uso: python -m app.db.seed_cartera [ruc]
Si no se indica RUC, usa RUC_DEMO = "20211683199".
"""

import random
import sys
from datetime import date, timedelta

from app.db import cartera_repository, user_repository
from app.tools.consultar_api_externa import consultar_ruc

RUC_DEMO = "20211683199"
CANTIDAD_FACTURAS = 100
HOY = date.today()

# Nombres de clientes deudores ficticios (no son empresas reales).
CLIENTES = [
    "Distribuidora Andina SAC", "Comercial Los Andes EIRL", "Grupo Ferretero del Sur SAC",
    "Textiles Pacifico SAC", "Inversiones Norte SRL", "Servicios Generales Lima SAC",
    "Constructora Vilcanota SAC", "Agroindustrias Chavin SAC", "Transportes Rapidos del Peru SAC",
    "Panaderia y Afines San Jose SAC", "Importaciones Maritimas SAC", "Farmacias Bienestar SAC",
    "Restaurantes Criollos Unidos SAC", "Mineria y Servicios Andinos SAC", "Papeleria Central SAC",
]

DESCRIPCIONES = [
    "Servicio de consultoria mensual", "Licencia de software (suscripcion anual)",
    "Venta de equipos de computo", "Mantenimiento de sistemas", "Soporte tecnico especializado",
    "Desarrollo de modulo a medida", "Capacitacion de personal", "Insumos de oficina",
]


def _estado_y_tramo(fecha_vencimiento: date, pagado: bool) -> tuple[str, int, str]:
    if pagado:
        return "pagado", 0, ""
    dias = (HOY - fecha_vencimiento).days
    if dias <= 0:
        return "pendiente", 0, "vigente"
    if dias <= 30:
        return "vencido", dias, "1-30"
    if dias <= 60:
        return "vencido", dias, "31-60"
    if dias <= 90:
        return "vencido", dias, "61-90"
    return "vencido", dias, "90+"


def _generar_factura(indice: int) -> dict:
    fecha_emision = HOY - timedelta(days=random.randint(10, 180))
    plazo_dias = random.choice([30, 45, 60, 90])
    fecha_vencimiento = fecha_emision + timedelta(days=plazo_dias)
    tipo = random.choice(["factura", "factura", "boleta"])

    return {
        "numero": f"{'F001' if tipo == 'factura' else 'B001'}-{1000 + indice}",
        "tipo_comprobante": tipo,
        "cliente_nombre": random.choice(CLIENTES),
        "cliente_ruc": None,
        "moneda": "PEN",
        "forma_pago": "credito",
        "fecha_emision": fecha_emision.isoformat(),
        "fecha_vencimiento": fecha_vencimiento.isoformat(),
        "monto_total": round(random.uniform(350, 18000), 2),
        "pagado": random.random() < 0.35,
    }


def _generar_detalle(factura_id: str, monto_total: float) -> list[dict]:
    cantidad_items = random.randint(1, 3)
    restante = monto_total
    filas = []
    for j in range(cantidad_items):
        es_ultimo = j == cantidad_items - 1
        subtotal = round(restante, 2) if es_ultimo else round(restante * random.uniform(0.2, 0.5), 2)
        restante -= subtotal
        cantidad = random.randint(1, 5)
        filas.append({
            "factura_id": factura_id,
            "descripcion": random.choice(DESCRIPCIONES),
            "cantidad": cantidad,
            "precio_unitario": round(subtotal / cantidad, 2),
            "subtotal": subtotal,
        })
    return filas


def seed(ruc: str = RUC_DEMO) -> None:
    usuario = user_repository.get_by_ruc(ruc)
    if usuario is None:
        datos = consultar_ruc(ruc)
        if datos is None:
            raise RuntimeError(
                f"No se encontro el RUC {ruc} en OpenRuc, no se puede sembrar la cartera."
            )
        usuario = user_repository.create(datos)
        print(f"Usuario {ruc} ({usuario['razon_social']}) registrado.")
    else:
        print(f"Usuario {ruc} ({usuario['razon_social']}) ya existia.")

    creadas = 0
    en_cartera = 0
    for i in range(CANTIDAD_FACTURAS):
        datos_factura = _generar_factura(i)
        pagado = datos_factura.pop("pagado")
        estado_pago, dias_vencido, tramo_mora = _estado_y_tramo(
            date.fromisoformat(datos_factura["fecha_vencimiento"]), pagado
        )

        factura = cartera_repository.insert_factura({
            **datos_factura,
            "emisor_ruc": ruc,
            "estado_pago": estado_pago,
        })
        creadas += 1

        detalle = _generar_detalle(factura["id"], float(datos_factura["monto_total"]))
        cartera_repository.insert_factura_detalle(detalle)

        if not pagado:
            cartera_repository.insert_cartera({
                "factura_id": factura["id"],
                "emisor_ruc": ruc,
                "monto_pendiente": datos_factura["monto_total"],
                "dias_vencido": dias_vencido,
                "tramo_mora": tramo_mora,
            })
            en_cartera += 1

    print(
        f"Sembradas {creadas} facturas a credito (PEN) para RUC {ruc}; "
        f"{en_cartera} quedaron en cartera (pendientes o vencidas)."
    )


if __name__ == "__main__":
    ruc_arg = sys.argv[1] if len(sys.argv) > 1 else RUC_DEMO
    seed(ruc_arg)
