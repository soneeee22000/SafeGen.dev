"""Tests for core.openai_client — Azure OpenAI wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.openai_client import AzureOpenAIClient, GenerationResult

# Test placeholder values (not real credentials)
_TEST_KEY = "test-placeholder"
_TEST_ENDPOINT = "https://custom.openai.azure.com/"


class TestAzureOpenAIClientInit:
    """Tests for client initialization."""

    def test_init_with_env_vars(self, mock_env: None) -> None:
        """Client initializes from environment variables."""
        with patch("core.openai_client.AzureOpenAI"):
            client = AzureOpenAIClient()
            assert client.endpoint == "https://test.openai.azure.com/"
            assert client.api_key == "test-key-12345"
            assert client.deployment == "gpt-4o"

    def test_init_with_explicit_params(self) -> None:
        """Client initializes from explicit parameters."""
        with patch("core.openai_client.AzureOpenAI"):
            test_key = _TEST_KEY
            client = AzureOpenAIClient(
                endpoint=_TEST_ENDPOINT,
                api_key=test_key,
                deployment="gpt-35-turbo",
                api_version="2024-01-01",
            )
            assert client.endpoint == _TEST_ENDPOINT
            assert client.deployment == "gpt-35-turbo"

    def test_init_missing_credentials_raises(self) -> None:
        """Client raises ValueError when credentials are missing."""
        with pytest.raises(ValueError, match="endpoint and API key are required"):
            AzureOpenAIClient(endpoint="", api_key="")


class TestAzureOpenAIClientGenerate:
    """Tests for the generate method."""

    def _make_mock_response(
        self,
        content: str = "Test response",
        model: str = "gpt-4o",
        prompt_tokens: int = 50,
        completion_tokens: int = 20,
    ) -> MagicMock:
        """Create a mock ChatCompletion response."""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = prompt_tokens
        mock_usage.completion_tokens = completion_tokens
        mock_usage.total_tokens = prompt_tokens + completion_tokens

        mock_message = MagicMock()
        mock_message.content = content

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = model
        mock_response.usage = mock_usage

        return mock_response

    def test_generate_basic_prompt(self, mock_env: None) -> None:
        """Generate with a simple prompt returns expected result."""
        mock_response = self._make_mock_response(content="Paris is the capital of France.")

        with patch("core.openai_client.AzureOpenAI") as mock_class:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = mock_response
            mock_class.return_value = mock_instance

            client = AzureOpenAIClient()
            result = client.generate(prompt="What is the capital of France?")

            assert isinstance(result, GenerationResult)
            assert result.content == "Paris is the capital of France."
            assert result.model == "gpt-4o"
            assert result.usage["total_tokens"] == 70
            assert result.finish_reason == "stop"

    def test_generate_with_context(self, mock_env: None) -> None:
        """Generate with context prepends context to the prompt."""
        mock_response = self._make_mock_response()

        with patch("core.openai_client.AzureOpenAI") as mock_class:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = mock_response
            mock_class.return_value = mock_instance

            client = AzureOpenAIClient()
            client.generate(prompt="Summarize this", context="Some document text here")

            # Verify the messages include context
            call_args = mock_instance.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages) == 2
            assert "Context:" in messages[1]["content"]
            assert "Some document text here" in messages[1]["content"]

    def test_generate_uses_custom_system_prompt(self, mock_env: None) -> None:
        """Custom system prompt overrides default."""
        mock_response = self._make_mock_response()

        with patch("core.openai_client.AzureOpenAI") as mock_class:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = mock_response
            mock_class.return_value = mock_instance

            client = AzureOpenAIClient()
            client.generate(prompt="test", system_prompt="You are a compliance checker.")

            call_args = mock_instance.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert messages[0]["content"] == "You are a compliance checker."

    def test_generate_without_context_no_prefix(self, mock_env: None) -> None:
        """Without context, prompt is sent directly without Context prefix."""
        mock_response = self._make_mock_response()

        with patch("core.openai_client.AzureOpenAI") as mock_class:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = mock_response
            mock_class.return_value = mock_instance

            client = AzureOpenAIClient()
            client.generate(prompt="Hello")

            call_args = mock_instance.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert messages[1]["content"] == "Hello"
