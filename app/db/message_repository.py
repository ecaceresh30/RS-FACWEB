from app.db.client import get_supabase_client
from app.resilience import with_retry


@with_retry
def add_message(conversacion_id: str, role: str, content: str) -> dict:
    client = get_supabase_client()
    response = (
        client.table("mensajes")
        .insert({"conversacion_id": conversacion_id, "role": role, "content": content})
        .execute()
    )
    return response.data[0]


@with_retry
def get_messages(conversacion_id: str) -> list[dict]:
    client = get_supabase_client()
    response = (
        client.table("mensajes")
        .select("*")
        .eq("conversacion_id", conversacion_id)
        .order("created_at")
        .execute()
    )
    return response.data


@with_retry
def delete_by_conversaciones(conversacion_ids: list[str]) -> None:
    """Borra todos los mensajes de las conversaciones dadas. Debe llamarse antes
    de borrar esas conversaciones (conversaciones.delete_by_usuario): mensajes
    referencia conversacion_id sin ON DELETE CASCADE."""
    if not conversacion_ids:
        return
    client = get_supabase_client()
    client.table("mensajes").delete().in_("conversacion_id", conversacion_ids).execute()
