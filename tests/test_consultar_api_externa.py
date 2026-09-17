from unittest.mock import MagicMock, patch

from app.tools.consultar_api_externa import consultar_ruc


@patch("app.tools.consultar_api_externa.requests.get")
def test_consultar_ruc_found(mock_get):
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "ruc": "20100047218",
        "razon_social": "BANCO DE CREDITO DEL PERU",
        "estado": "ACTIVO",
        "condicion": "HABIDO",
        "direccion": "JR. CENTENARIO NRO 156",
        "ubigeo": "150114",
        "source": "SUNAT",
        "as_of": "2026-05-30",
        "_more": {"ignorar": "esto"},
    }
    mock_get.return_value = mock_response

    datos = consultar_ruc("20100047218")

    assert datos == {
        "ruc": "20100047218",
        "razon_social": "BANCO DE CREDITO DEL PERU",
        "estado": "ACTIVO",
        "condicion": "HABIDO",
        "direccion": "JR. CENTENARIO NRO 156",
        "ubigeo": "150114",
        "source": "SUNAT",
        "as_of": "2026-05-30",
    }
    mock_get.assert_called_once_with(
        "https://openruc.com/api/ruc/20100047218", timeout=10
    )


@patch("app.tools.consultar_api_externa.requests.get")
def test_consultar_ruc_not_found(mock_get):
    mock_get.return_value = MagicMock(status_code=404)

    assert consultar_ruc("99999999999") is None


@patch("app.tools.consultar_api_externa.requests.get")
def test_consultar_ruc_raises_on_server_error(mock_get):
    import requests

    mock_response = MagicMock(status_code=500)
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
    mock_get.return_value = mock_response

    try:
        consultar_ruc("20100047218")
        assert False, "deberia haber lanzado HTTPError"
    except requests.exceptions.HTTPError:
        pass
