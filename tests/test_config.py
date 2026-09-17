import pytest

from app.config import load_settings


def test_load_settings_raises_when_missing_required_vars(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(RuntimeError):
        load_settings()


def test_load_settings_returns_values_when_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    settings = load_settings()

    assert settings.openai_api_key == "sk-test"
    assert settings.openai_model == "gpt-4.1"
    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_service_role_key == "test-key"
