from unittest.mock import MagicMock, patch

from app.conversation import (
    RUC_PATTERN,
    RUC_SEARCH_PATTERN,
    RucInvalidoError,
    RucNoEncontradoError,
    Sesion,
    TurnoError,
    _build_augmented_user_message,
    _format_empresa_info,
    _format_sources,
    _strip_fuente_suffix,
    cargar_historial,
    iniciar_sesion,
    procesar_turno,
)


def test_ruc_pattern_accepts_11_digits():
    assert RUC_PATTERN.fullmatch("20123456789")


def test_ruc_pattern_rejects_wrong_length():
    assert RUC_PATTERN.fullmatch("123") is None
    assert RUC_PATTERN.fullmatch("201234567890") is None


def test_ruc_pattern_rejects_non_numeric():
    assert RUC_PATTERN.fullmatch("2012345678a") is None


def test_ruc_search_pattern_matches_basic_phrasing():
    match = RUC_SEARCH_PATTERN.search("busca ruc 20100047218")
    assert match.group(1) == "20100047218"


def test_ruc_search_pattern_matches_with_articles_and_case_insensitive():
    match = RUC_SEARCH_PATTERN.search("Busca al RUC 20100047218 porfavor")
    assert match.group(1) == "20100047218"

    match2 = RUC_SEARCH_PATTERN.search("busca el ruc 20456789123")
    assert match2.group(1) == "20456789123"


def test_ruc_search_pattern_no_match_without_ruc_number():
    assert RUC_SEARCH_PATTERN.search("busca en internet el clima") is None


def test_format_empresa_info():
    datos = {
        "ruc": "20100047218",
        "razon_social": "BANCO DE CREDITO DEL PERU",
        "estado": "ACTIVO",
        "condicion": "HABIDO",
        "direccion": "JR. CENTENARIO NRO 156",
        "ubigeo": "150114",
    }

    resultado = _format_empresa_info(datos)

    assert "20100047218" in resultado
    assert "BANCO DE CREDITO DEL PERU" in resultado
    assert "ACTIVO" in resultado
    assert "HABIDO" in resultado


def test_build_augmented_user_message_with_context():
    msg = _build_augmented_user_message("cual es el mecanismo de envio?", "contenido relevante")

    assert msg["role"] == "user"
    assert "cual es el mecanismo de envio?" in msg["content"]
    assert "contenido relevante" in msg["content"]


def test_build_augmented_user_message_without_context():
    msg = _build_augmented_user_message("hola", "")

    assert "hola" in msg["content"]
    assert "sin resultados relevantes" in msg["content"]


def test_format_sources_with_page():
    fuentes = [{"source": "conocimiento.pdf", "page": 12}]

    assert _format_sources(fuentes) == "Fuente: conocimiento.pdf, pag. 12"


def test_format_sources_groups_pages_under_same_source():
    fuentes = [
        {"source": "conocimiento.pdf", "page": 3},
        {"source": "conocimiento.pdf", "page": 27},
        {"source": "conocimiento.pdf", "page": 6},
    ]

    assert _format_sources(fuentes) == "Fuente: conocimiento.pdf, pag. 3,27,6"


def test_format_sources_deduplicates_same_page():
    fuentes = [
        {"source": "conocimiento.pdf", "page": 12},
        {"source": "conocimiento.pdf", "page": 12},
        {"source": "conocimiento.pdf", "page": 5},
    ]

    assert _format_sources(fuentes) == "Fuente: conocimiento.pdf, pag. 12,5"


def test_format_sources_without_page():
    fuentes = [{"source": "conocimiento.pdf", "page": None}]

    assert _format_sources(fuentes) == "Fuente: conocimiento.pdf"


def test_strip_fuente_suffix_removes_pdf_citation():
    content = "Los requisitos son X, Y, Z.\n\nFuente: conocimiento.pdf, pag. 3,27,6"

    assert _strip_fuente_suffix(content) == "Los requisitos son X, Y, Z."


def test_strip_fuente_suffix_removes_openruc_citation():
    content = "RUC: 20100047218\nRazon social: BCP\n\nFuente: OpenRuc"

    assert _strip_fuente_suffix(content) == "RUC: 20100047218\nRazon social: BCP"


def test_strip_fuente_suffix_no_op_when_no_citation():
    content = "Hola, en que puedo ayudarte?"

    assert _strip_fuente_suffix(content) == content


@patch("app.conversation.message_repository.get_messages")
def test_cargar_historial_strips_fuente_from_assistant_turns(mock_get_messages):
    mock_get_messages.return_value = [
        {"role": "user", "content": "cuales son los requisitos?"},
        {
            "role": "assistant",
            "content": "Son X, Y, Z.\n\nFuente: conocimiento.pdf, pag. 3,27,6",
        },
    ]

    messages = cargar_historial("conv-1")

    assert messages[0]["content"] == "cuales son los requisitos?"
    assert messages[1]["content"] == "Son X, Y, Z."


def test_iniciar_sesion_rejects_invalid_ruc():
    try:
        iniciar_sesion("123")
        assert False, "deberia haber lanzado RucInvalidoError"
    except RucInvalidoError:
        pass


@patch("app.conversation.build_agent")
@patch("app.conversation.cargar_historial")
@patch("app.conversation.consultar_ruc")
@patch("app.conversation.user_repository")
@patch("app.conversation.conversation_repository")
def test_iniciar_sesion_new_ruc_registers_via_openruc(
    mock_conv_repo, mock_user_repo, mock_consultar_ruc, mock_cargar_historial, mock_build_agent
):
    mock_user_repo.get_by_ruc.return_value = None
    datos = {"ruc": "20100047218", "razon_social": "BCP"}
    mock_consultar_ruc.return_value = datos
    mock_user_repo.create.return_value = datos
    mock_conv_repo.create_conversation.return_value = {"id": "conv-1"}
    mock_cargar_historial.return_value = []
    mock_build_agent.return_value = MagicMock()

    sesion = iniciar_sesion("20100047218")

    assert sesion.es_nuevo is True
    assert sesion.usuario == datos
    mock_user_repo.create.assert_called_once_with(datos)


@patch("app.conversation.consultar_ruc")
@patch("app.conversation.user_repository")
def test_iniciar_sesion_new_ruc_not_found_raises(mock_user_repo, mock_consultar_ruc):
    mock_user_repo.get_by_ruc.return_value = None
    mock_consultar_ruc.return_value = None

    try:
        iniciar_sesion("20999999999")
        assert False, "deberia haber lanzado RucNoEncontradoError"
    except RucNoEncontradoError:
        pass


def _fake_sesion(agent) -> Sesion:
    return Sesion(
        usuario={"ruc": "20100047218", "razon_social": "BCP"},
        conversacion={"id": "conv-1"},
        messages=[],
        es_nuevo=False,
        agent_sin_internet=agent,
        agent_con_internet=agent,
    )


@patch("app.conversation.conversation_repository")
@patch("app.conversation.message_repository")
@patch("app.conversation.consultar_ruc")
def test_procesar_turno_ruc_search_command(mock_consultar_ruc, mock_message_repo, mock_conv_repo):
    mock_consultar_ruc.return_value = {
        "ruc": "20456789123",
        "razon_social": "OTRA EMPRESA",
        "estado": "ACTIVO",
        "condicion": "HABIDO",
        "direccion": "AV. X",
        "ubigeo": "150101",
    }
    sesion = _fake_sesion(agent=MagicMock())

    resultado = procesar_turno(sesion, "busca el ruc 20456789123")

    assert "OTRA EMPRESA" in resultado.respuesta
    assert resultado.respuesta.endswith("Fuente: OpenRuc")
    assert "OTRA EMPRESA" in sesion.messages[-1]["content"]
    assert "Fuente" not in sesion.messages[-1]["content"]


@patch("app.conversation.conversation_repository")
@patch("app.conversation.message_repository")
@patch("app.conversation.retrieve_context")
def test_procesar_turno_normal_question_uses_agent(mock_retrieve_context, mock_message_repo, mock_conv_repo):
    mock_retrieve_context.return_value = ("", [])
    agent = MagicMock()
    agent.invoke.return_value = {"messages": [MagicMock(content="Hola!")]}
    sesion = _fake_sesion(agent=agent)

    resultado = procesar_turno(sesion, "hola")

    assert resultado.respuesta == "Hola!"
    agent.invoke.assert_called_once()


@patch("app.conversation.conversation_repository")
@patch("app.conversation.message_repository")
@patch("app.conversation.obtener_contexto_recomendaciones")
@patch("app.conversation.obtener_resumen_cartera")
@patch("app.conversation.retrieve_context")
def test_procesar_turno_cartera_question_injects_resumen_into_agent_call(
    mock_retrieve_context,
    mock_obtener_resumen_cartera,
    mock_obtener_contexto_recomendaciones,
    mock_message_repo,
    mock_conv_repo,
):
    mock_retrieve_context.return_value = ("algo irrelevante", [{"source": "conocimiento.pdf"}])
    mock_obtener_resumen_cartera.return_value = "Monto total pendiente: S/ 1,000.00"
    mock_obtener_contexto_recomendaciones.return_value = (
        "contenido completo de recomendaciones",
        [{"source": "recomendaciones_cartera.pdf", "page": 1}],
    )
    agent = MagicMock()
    agent.invoke.return_value = {"messages": [MagicMock(content="Tu cartera esta sana.")]}
    sesion = _fake_sesion(agent=agent)

    resultado = procesar_turno(sesion, "como esta mi cartera?")

    assert resultado.respuesta.startswith("Tu cartera esta sana.")
    mock_obtener_resumen_cartera.assert_called_once_with("20100047218")
    invoke_args = agent.invoke.call_args[0][0]
    contenido = invoke_args["messages"][-1]["content"]
    assert "Datos de tu cartera de cuentas por cobrar" in contenido
    # El contexto completo de recomendaciones reemplaza al top-K generico.
    assert "contenido completo de recomendaciones" in contenido
    assert "algo irrelevante" not in contenido
    assert "Fuente: recomendaciones_cartera.pdf, pag. 1" in resultado.respuesta


@patch("app.conversation.conversation_repository")
@patch("app.conversation.message_repository")
@patch("app.conversation.retrieve_context")
def test_procesar_turno_without_cartera_keyword_skips_cartera_lookup(
    mock_retrieve_context, mock_message_repo, mock_conv_repo
):
    mock_retrieve_context.return_value = ("", [])
    agent = MagicMock()
    agent.invoke.return_value = {"messages": [MagicMock(content="Hola!")]}
    sesion = _fake_sesion(agent=agent)

    procesar_turno(sesion, "hola")

    invoke_args = agent.invoke.call_args[0][0]
    assert "Datos de tu cartera" not in invoke_args["messages"][-1]["content"]


@patch("app.conversation.conversation_repository")
@patch("app.conversation.message_repository")
@patch("app.conversation.consultar_ruc", side_effect=RuntimeError("boom"))
def test_procesar_turno_ruc_search_error_raises_turno_error(mock_consultar_ruc, mock_message_repo, mock_conv_repo):
    sesion = _fake_sesion(agent=MagicMock())

    try:
        procesar_turno(sesion, "busca el ruc 20456789123")
        assert False, "deberia haber lanzado TurnoError"
    except TurnoError:
        pass
