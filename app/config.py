import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

_REQUIRED_VARS = (
    "OPENAI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    supabase_url: str
    supabase_service_role_key: str
    tavily_api_key: str | None


def load_settings() -> Settings:
    missing = [name for name in _REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Faltan variables de entorno requeridas: "
            f"{', '.join(missing)}. Revisa tu archivo .env (ver .env.example)."
        )

    return Settings(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_service_role_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
    )
