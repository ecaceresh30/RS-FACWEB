from unittest.mock import patch

from app.tools.consultar_cartera import (
    MAX_PREGUNTAS_SUGERIDAS,
    obtener_resumen_cartera,
    obtener_tabla_cartera,
    seleccionar_tabla_cartera,
    sugerir_preguntas_cartera,
    wants_cartera_consulta,
    wants_recomendacion_cartera,
)

_FILAS_CARTERA_EJEMPLO = [
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
    mock_get_cartera.return_value = _FILAS_CARTERA_EJEMPLO

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


def test_wants_recomendacion_cartera_true_for_recommendation_phrasings():
    assert wants_recomendacion_cartera("que me recomiendas hacer con mi cartera?")
    assert wants_recomendacion_cartera("me conviene el factoring?")
    assert wants_recomendacion_cartera("que deberia hacer con mi cartera?")
    assert wants_recomendacion_cartera("evalua mi cartera")


def test_wants_recomendacion_cartera_false_for_factual_questions():
    assert not wants_recomendacion_cartera("a cuanto asciende el monto total de mi cartera?")
    assert not wants_recomendacion_cartera("como se distribuye mi cartera por tramo de mora?")


def test_wants_recomendacion_cartera_ignores_substring_false_positives():
    """"caja" y "opcion" son stems cortos que aparecen dentro de otras palabras
    sin relacion (encaja, adopcion); solo deben matchear al inicio de palabra."""
    assert not wants_recomendacion_cartera("el saldo de mi cartera encaja con lo esperado")
    assert not wants_recomendacion_cartera("la adopcion de este sistema en mi cartera")


@patch("app.tools.consultar_cartera.cartera_repository.get_cartera")
def test_obtener_tabla_cartera_none_when_no_rows(mock_get_cartera):
    mock_get_cartera.return_value = []

    assert obtener_tabla_cartera("20211683199") is None


@patch("app.tools.consultar_cartera.cartera_repository.get_cartera")
def test_obtener_tabla_cartera_matches_resumen_data(mock_get_cartera):
    mock_get_cartera.return_value = _FILAS_CARTERA_EJEMPLO

    tabla = obtener_tabla_cartera("20211683199")

    assert tabla["total_facturas"] == 3
    assert tabla["monto_total"] == 1700.0
    assert tabla["tramos"] == [
        {"tramo": "vigente", "cantidad": 1, "monto": 1000.0},
        {"tramo": "31-60", "cantidad": 1, "monto": 500.0},
        {"tramo": "90+", "cantidad": 1, "monto": 200.0},
    ]
    # Facturas vencidas ordenadas por dias_vencido descendente, igual que el resumen textual.
    assert [f["numero"] for f in tabla["facturas_vencidas"]] == ["F001-3", "F001-2"]
    assert tabla["facturas_vencidas"][0] == {
        "numero": "F001-3",
        "cliente": "Cliente C",
        "monto": 200.0,
        "dias_vencido": 95,
    }


_TABLA_EJEMPLO = {
    "total_facturas": 3,
    "monto_total": 1700.0,
    "tramos": [{"tramo": "vigente", "cantidad": 1, "monto": 1000.0}],
    "facturas_vencidas": [{"numero": "F001-3", "cliente": "Cliente C", "monto": 200.0, "dias_vencido": 95}],
}


def test_seleccionar_tabla_cartera_none_passthrough():
    assert seleccionar_tabla_cartera(None, "a cuanto asciende mi cartera?") is None


def test_seleccionar_tabla_cartera_pregunta_puntual_de_monto_no_muestra_tabla():
    """Pedir solo el monto (una cifra, no una lista) no debe traer ninguna
    tabla, aunque obtener_tabla_cartera haya calculado tramos/vencidas."""
    resultado = seleccionar_tabla_cartera(_TABLA_EJEMPLO, "a cuanto asciende el monto total?")

    assert resultado is None


def test_seleccionar_tabla_cartera_pregunta_de_tramos_solo_incluye_tramos():
    resultado = seleccionar_tabla_cartera(_TABLA_EJEMPLO, "como se distribuye mi cartera por tramo de mora?")

    assert resultado["tramos"] == _TABLA_EJEMPLO["tramos"]
    assert resultado["facturas_vencidas"] == []


def test_seleccionar_tabla_cartera_pregunta_de_facturas_solo_incluye_vencidas():
    resultado = seleccionar_tabla_cartera(_TABLA_EJEMPLO, "cuales son las facturas mas vencidas de mi cartera?")

    assert resultado["facturas_vencidas"] == _TABLA_EJEMPLO["facturas_vencidas"]
    assert resultado["tramos"] == []


def test_seleccionar_tabla_cartera_pregunta_abierta_incluye_tramos_no_facturas():
    """Sin ninguna categoria puntual (pregunta abierta), se muestra el
    agregado por tramo, pero NO el detalle nominal de facturas/clientes (mas
    sensible) a menos que se pida explicitamente."""
    resultado = seleccionar_tabla_cartera(_TABLA_EJEMPLO, "como esta mi cartera?")

    assert resultado["tramos"] == _TABLA_EJEMPLO["tramos"]
    assert resultado["facturas_vencidas"] == []


def test_seleccionar_tabla_cartera_pregunta_no_financiera_no_filtra_facturas_nominales():
    """Bug reportado: "cartera"/"cliente" pueden aparecer en una pregunta que
    no tiene nada que ver con cuentas por cobrar (ej. marketing). El gate de
    "cartera" es literal y puede activarse igual (limitacion ya documentada),
    pero no debe filtrar deuda real de clientes con nombre y monto por esa
    coincidencia de palabra."""
    resultado = seleccionar_tabla_cartera(
        _TABLA_EJEMPLO,
        "quiero hacer crecer mi cartera de clientes potenciales, dame consejos de marketing",
    )

    assert resultado["facturas_vencidas"] == []


def test_seleccionar_tabla_cartera_pregunta_de_recomendacion_no_muestra_tabla():
    """Pedir solo una recomendacion produce un analisis en prosa, no una
    lista de tramos/facturas: no corresponde ninguna tabla (bug reportado:
    "que recomendaciones de factoring tienes" traia ambas tablas de todas
    formas porque no mencionaba monto/tramo/factura explicitamente)."""
    resultado = seleccionar_tabla_cartera(
        _TABLA_EJEMPLO, "¿Qué recomendaciones de factoring o financiamiento tienes para mi cartera?"
    )

    assert resultado is None


def test_seleccionar_tabla_cartera_recomendacion_mas_tramos_incluye_solo_tramos():
    resultado = seleccionar_tabla_cartera(
        _TABLA_EJEMPLO, "como se distribuye por tramo de mora y que me recomiendas?"
    )

    assert resultado["tramos"] == _TABLA_EJEMPLO["tramos"]
    assert resultado["facturas_vencidas"] == []
