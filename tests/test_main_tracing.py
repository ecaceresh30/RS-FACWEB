from app.main import _tracing_enabled


def test_tracing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    assert _tracing_enabled() is False


def test_tracing_enabled_via_langsmith_var(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    assert _tracing_enabled() is True


def test_tracing_enabled_via_legacy_langchain_var(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    assert _tracing_enabled() is True
