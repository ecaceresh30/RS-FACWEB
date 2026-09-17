from unittest.mock import MagicMock, patch

from app.tools.buscar_conocimiento import buscar_conocimiento, retrieve_context


@patch("app.tools.buscar_conocimiento.get_supabase_client")
@patch("app.tools.buscar_conocimiento.OpenAIEmbeddings")
@patch("app.tools.buscar_conocimiento.load_settings")
def test_retrieve_context_returns_content_and_sources(
    mock_settings, mock_embeddings_cls, mock_get_client
):
    mock_settings.return_value = MagicMock(openai_api_key="sk-test")
    mock_embeddings_cls.return_value.embed_query.return_value = [0.1, 0.2]

    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(
        data=[
            {
                "content": "chunk 1",
                "similarity": 0.6,
                "metadata": {"source": "conocimiento.pdf", "page": 3},
            },
            {
                "content": "chunk 2",
                "similarity": 0.55,
                "metadata": {"source": "conocimiento.pdf", "page": 5},
            },
        ]
    )
    mock_get_client.return_value = client

    contexto, fuentes = retrieve_context("que es X")

    assert contexto == "chunk 1\n\n---\n\nchunk 2"
    assert fuentes == [
        {"source": "conocimiento.pdf", "page": 3},
        {"source": "conocimiento.pdf", "page": 5},
    ]


@patch("app.tools.buscar_conocimiento.get_supabase_client")
@patch("app.tools.buscar_conocimiento.OpenAIEmbeddings")
@patch("app.tools.buscar_conocimiento.load_settings")
def test_retrieve_context_filters_out_low_similarity_matches(
    mock_settings, mock_embeddings_cls, mock_get_client
):
    mock_settings.return_value = MagicMock(openai_api_key="sk-test")
    mock_embeddings_cls.return_value.embed_query.return_value = [0.1]

    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(
        data=[
            {"content": "irrelevante", "similarity": 0.28, "metadata": {"source": "x.pdf"}},
        ]
    )
    mock_get_client.return_value = client

    contexto, fuentes = retrieve_context("hola, como estas?")

    assert contexto == ""
    assert fuentes == []


@patch("app.tools.buscar_conocimiento.get_supabase_client")
@patch("app.tools.buscar_conocimiento.OpenAIEmbeddings")
@patch("app.tools.buscar_conocimiento.load_settings")
def test_retrieve_context_no_matches(mock_settings, mock_embeddings_cls, mock_get_client):
    mock_settings.return_value = MagicMock(openai_api_key="sk-test")
    mock_embeddings_cls.return_value.embed_query.return_value = [0.1]

    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=[])
    mock_get_client.return_value = client

    assert retrieve_context("algo inexistente") == ("", [])


@patch("app.tools.buscar_conocimiento.get_supabase_client")
@patch("app.tools.buscar_conocimiento.OpenAIEmbeddings")
@patch("app.tools.buscar_conocimiento.load_settings")
def test_buscar_conocimiento_tool_returns_content(
    mock_settings, mock_embeddings_cls, mock_get_client
):
    mock_settings.return_value = MagicMock(openai_api_key="sk-test")
    mock_embeddings_cls.return_value.embed_query.return_value = [0.1, 0.2]

    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(
        data=[{"content": "chunk 1", "similarity": 0.6, "metadata": {"source": "x.pdf"}}]
    )
    mock_get_client.return_value = client

    result = buscar_conocimiento.invoke({"consulta": "que es X"})

    assert "chunk 1" in result


@patch("app.tools.buscar_conocimiento.get_supabase_client")
@patch("app.tools.buscar_conocimiento.OpenAIEmbeddings")
@patch("app.tools.buscar_conocimiento.load_settings")
def test_buscar_conocimiento_tool_no_matches(mock_settings, mock_embeddings_cls, mock_get_client):
    mock_settings.return_value = MagicMock(openai_api_key="sk-test")
    mock_embeddings_cls.return_value.embed_query.return_value = [0.1]

    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=[])
    mock_get_client.return_value = client

    result = buscar_conocimiento.invoke({"consulta": "algo inexistente"})

    assert "No se encontro informacion relevante" in result
