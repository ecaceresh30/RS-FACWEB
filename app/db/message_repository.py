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
