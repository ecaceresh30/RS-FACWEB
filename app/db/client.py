from functools import lru_cache

from supabase import Client, create_client

from app.config import load_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    settings = load_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
