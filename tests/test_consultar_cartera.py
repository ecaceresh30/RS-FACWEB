from unittest.mock import patch

from app.tools.consultar_cartera import (
    MAX_PREGUNTAS_SUGERIDAS,
    obtener_resumen_cartera,
    sugerir_preguntas_cartera,
    wants_cartera_consulta,
)


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


def test_sugerir_preguntas_cartera_caps_at_max_and_mentions_cartera():
    sugerencias = sugerir_preguntas_cartera("como esta mi cartera?")

    assert len(sugerencias) <= MAX_PREGUNTAS_SUGERIDAS
    assert all("cartera" in p.lower() for p in sugerencias)


def test_sugerir_preguntas_cartera_excludes_category_already_asked():
    sugerencias = sugerir_preguntas_cartera("a cuanto asciende el monto total de mi cartera?")

    assert not any("monto total pendiente" in p.lower() for p in sugerencias)


def test_sugerir_preguntas_cartera_excludes_recomendacion_if_already_asked():
    sugerencias = sugerir_preguntas_cartera("me recomiendas el factoring para mi cartera?")

    assert not any("recomendaciones de factoring" in p.lower() for p in sugerencias)
