from unittest.mock import MagicMock, patch

import httpx

from app.db import user_repository


def _mock_client_with_response(data):
    client = MagicMock()
    query = MagicMock()
    client.table.return_value = query
    query.select.return_value = query
    query.insert.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    query.execute.return_value = MagicMock(data=data)
    return client


@patch("app.db.user_repository.get_supabase_client")
def test_get_by_ruc_found(mock_get_client):
    mock_get_client.return_value = _mock_client_with_response(
        [{"ruc": "20123456789"}]
    )

    result = user_repository.get_by_ruc("20123456789")

    assert result == {"ruc": "20123456789"}


@patch("app.db.user_repository.get_supabase_client")
def test_get_by_ruc_not_found(mock_get_client):
    mock_get_client.return_value = _mock_client_with_response([])

    result = user_repository.get_by_ruc("99999999999")

    assert result is None


@patch("app.db.user_repository.get_supabase_client")
def test_get_by_ruc_retries_on_transient_network_error(mock_get_client):
    client = _mock_client_with_response([{"ruc": "20123456789"}])
    client.table.return_value.execute.side_effect = [
        httpx.ConnectError("boom"),
        MagicMock(data=[{"ruc": "20123456789"}]),
    ]
    mock_get_client.return_value = client

    result = user_repository.get_by_ruc("20123456789")

    assert result == {"ruc": "20123456789"}
    assert client.table.return_value.execute.call_count == 2


@patch("app.db.user_repository.create")
@patch("app.db.user_repository.get_by_ruc")
def test_get_or_create_existing_user(mock_get_by_ruc, mock_create):
    mock_get_by_ruc.return_value = {"ruc": "20123456789"}

    usuario, creado = user_repository.get_or_create({"ruc": "20123456789"})

    assert usuario == {"ruc": "20123456789"}
    assert creado is False
    mock_create.assert_not_called()


@patch("app.db.user_repository.create")
@patch("app.db.user_repository.get_by_ruc")
def test_get_or_create_new_user(mock_get_by_ruc, mock_create):
    mock_get_by_ruc.return_value = None
    datos = {"ruc": "20456789123", "razon_social": "ACME SAC"}
    mock_create.return_value = datos

    usuario, creado = user_repository.get_or_create(datos)

    assert usuario == datos
    assert creado is True
    mock_create.assert_called_once_with(datos)
