from app.db.client import get_supabase_client
from app.resilience import with_retry


@with_retry
def get_cartera(emisor_ruc: str) -> list[dict]:
    """Trae las facturas a credito (cartera de cuentas por cobrar) de
    `emisor_ruc`, con los datos de la factura asociada."""
    client = get_supabase_client()
    response = (
        client.table("cartera")
        .select(
            "monto_pendiente, dias_vencido, tramo_mora, "
            "facturas(numero, cliente_nombre, moneda, fecha_vencimiento, monto_total)"
        )
        .eq("emisor_ruc", emisor_ruc)
        .execute()
    )
    return response.data


@with_retry
def insert_factura(factura: dict) -> dict:
    client = get_supabase_client()
    response = client.table("facturas").insert(factura).execute()
    return response.data[0]


@with_retry
def insert_factura_detalle(filas: list[dict]) -> None:
    if not filas:
        return
    client = get_supabase_client()
    client.table("factura_detalle").insert(filas).execute()


@with_retry
def insert_cartera(fila: dict) -> dict:
    client = get_supabase_client()
    response = client.table("cartera").insert(fila).execute()
    return response.data[0]
