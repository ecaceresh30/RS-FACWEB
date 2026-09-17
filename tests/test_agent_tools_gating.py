from app.agent.agent import get_tools, wants_internet_search
from app.tools.busqueda_internet import busqueda_internet


def test_wants_internet_search_detects_trigger_phrase():
    assert wants_internet_search("Busca en internet el clima de hoy") is True
    assert wants_internet_search("BUSCA EN INTERNET algo") is True


def test_wants_internet_search_false_without_trigger_phrase():
    assert wants_internet_search("dime el clima de hoy") is False
    assert wants_internet_search("busca en la base de conocimiento") is False


def test_get_tools_excludes_busqueda_internet_by_default():
    tools = get_tools(include_busqueda_internet=False)

    assert busqueda_internet not in tools


def test_get_tools_includes_busqueda_internet_when_requested():
    tools = get_tools(include_busqueda_internet=True)

    assert busqueda_internet in tools
