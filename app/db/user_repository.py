from app.db.client import get_supabase_client
from app.resilience import with_retry


@with_retry
def get_by_ruc(ruc: str) -> dict | None:
    client = get_supabase_client()
    response = client.table("usuarios").select("*").eq("ruc", ruc).limit(1).execute()
    rows = response.data
    return rows[0] if rows else None


@with_retry
def create(datos: dict) -> dict:
    """Registra un usuario nuevo. `datos` es el dict devuelto por OpenRuc
    (incluye "ruc") - se cachea tal cual en Supabase."""
    client = get_supabase_client()
    response = client.table("usuarios").insert(datos).execute()
    return response.data[0]


def get_or_create(datos: dict) -> tuple[dict, bool]:
    """Devuelve (usuario, creado). `creado` es True si el RUC no existia."""
    usuario = get_by_ruc(datos["ruc"])
    if usuario is not None:
        return usuario, False
    return create(datos), True
