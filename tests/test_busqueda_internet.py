from unittest.mock import MagicMock, patch

from app.tools.busqueda_internet import busqueda_internet


@patch("app.tools.busqueda_internet.TavilyClient")
@patch("app.tools.busqueda_internet.load_settings")
def test_busqueda_internet_sin_api_key_devuelve_mensaje_claro(mock_settings, mock_client_cls):
    mock_settings.return_value = MagicMock(tavily_api_key=None)

    result = busqueda_internet.invoke({"consulta": "clima en Lima"})

    assert "no esta configurada" in result
    mock_client_cls.assert_not_called()


@patch("app.tools.busqueda_internet.TavilyClient")
@patch("app.tools.busqueda_internet.load_settings")
def test_busqueda_internet_con_resultados(mock_settings, mock_client_cls):
    mock_settings.return_value = MagicMock(tavily_api_key="tvly-test")
    mock_client_cls.return_value.search.return_value = {
        "results": [
            {"title": "Titulo 1", "url": "https://a.com", "content": "contenido 1"},
        ]
    }

    result = busqueda_internet.invoke({"consulta": "clima en Lima"})

    assert "Titulo 1" in result
    assert "contenido 1" in result


@patch("app.tools.busqueda_internet.TavilyClient")
@patch("app.tools.busqueda_internet.load_settings")
def test_busqueda_internet_sin_resultados(mock_settings, mock_client_cls):
    mock_settings.return_value = MagicMock(tavily_api_key="tvly-test")
    mock_client_cls.return_value.search.return_value = {"results": []}

    result = busqueda_internet.invoke({"consulta": "algo muy raro"})

    assert "No se encontraron resultados" in result
