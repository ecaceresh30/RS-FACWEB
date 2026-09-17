from datetime import UTC, datetime

from app.db.client import get_supabase_client
from app.resilience import with_retry


@with_retry
def create_conversation(usuario_ruc: str) -> dict:
    client = get_supabase_client()
    response = client.table("conversaciones").insert({"usuario_ruc": usuario_ruc}).execute()
    return response.data[0]


@with_retry
def get_conversations_by_usuario(usuario_ruc: str) -> list[dict]:
    client = get_supabase_client()
    response = (
        client.table("conversaciones")
        .select("*")
        .eq("usuario_ruc", usuario_ruc)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_latest_conversation(usuario_ruc: str) -> dict | None:
    conversaciones = get_conversations_by_usuario(usuario_ruc)
    return conversaciones[0] if conversaciones else None


@with_retry
def touch_conversation(conversacion_id: str) -> None:
    client = get_supabase_client()
    now = datetime.now(UTC).isoformat()
    client.table("conversaciones").update({"updated_at": now}).eq(
        "id", conversacion_id
    ).execute()
