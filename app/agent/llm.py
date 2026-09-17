from langchain_openai import ChatOpenAI

from app.config import load_settings


def get_llm() -> ChatOpenAI:
    settings = load_settings()
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
