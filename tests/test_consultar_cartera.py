from unittest.mock import patch

from app.tools.consultar_cartera import obtener_resumen_cartera, wants_cartera_consulta


def test_wants_cartera_consulta_matches_case_insensitive():
    assert wants_cartera_consulta("como esta mi cartera?")
    assert wants_cartera_consulta("CUAL ES MI CARTERA DE COBRANZA")
    assert not wants_cartera_consulta("hola, como estas?")


@patch("app.tools.consultar_cartera.cartera_repository.get_cartera")
def test_obtener_resumen_cartera_empty_when_no_rows(mock_get_cartera):
    mock_get_cartera.return_value = []

    assert obtener_resumen_cartera("20211683199") == ""


@patch("app.tools.consultar_cartera.cartera_repository.get_cartera")
def test_obtener_resumen_cartera_aggregates_by_tramo_and_lists_overdue(mock_get_cartera):
    mock_get_cartera.return_value = [
        {
            "monto_pendiente": 1000.0,
            "dias_vencido": 0,
            "tramo_mora": "vigente",
            "facturas": {"numero": "F001-1", "cliente_nombre": "Cliente A"},
        },
        {
            "monto_pendiente": 500.0,
            "dias_vencido": 45,
            "tramo_mora": "31-60",
            "facturas": {"numero": "F001-2", "cliente_nombre": "Cliente B"},
        },
        {
            "monto_pendiente": 200.0,
            "dias_vencido": 95,
            "tramo_mora": "90+",
            "facturas": {"numero": "F001-3", "cliente_nombre": "Cliente C"},
        },
    ]

    resumen = obtener_resumen_cartera("20211683199")

    assert "3 facturas a credito en soles" in resumen
    assert "S/ 1,700.00" in resumen
    assert "- vigente: 1 facturas, S/ 1,000.00" in resumen
    assert "- 31-60: 1 facturas, S/ 500.00" in resumen
    assert "- 90+: 1 facturas, S/ 200.00" in resumen
    # Ordenadas por dias_vencido descendente
    assert resumen.index("F001-3") < resumen.index("F001-2")
    assert "F001-1" not in resumen  # vigente, no aparece en "vencidas"
