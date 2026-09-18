from unittest.mock import MagicMock, patch

from app.agent.llm import MAX_OUTPUT_TOKENS, get_llm


@patch("app.agent.llm.ChatOpenAI")
@patch("app.agent.llm.load_settings")
def test_get_llm_sets_max_tokens_ceiling(mock_settings, mock_chat_openai_cls):
    mock_settings.return_value = MagicMock(
        openai_api_key="sk-test", openai_model="gpt-4.1"
    )
    mock_chat_openai_cls.return_value = MagicMock()

    get_llm()

    mock_chat_openai_cls.assert_called_once_with(
        model="gpt-4.1", api_key="sk-test", max_tokens=MAX_OUTPUT_TOKENS
    )
