"""Shared test fixtures for SafeGen."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.openai_client import AzureOpenAIClient, GenerationResult


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for testing."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=test")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER_RULES", "compliance-rules")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER_AUDIT", "audit-logs")


@pytest.fixture()
def sample_generation_result() -> GenerationResult:
    """A sample successful generation result."""
    return GenerationResult(
        content="This is a safe and helpful response.",
        model="gpt-4o",
        usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        finish_reason="stop",
    )


@pytest.fixture()
def mock_openai_client(sample_generation_result: GenerationResult) -> MagicMock:
    """A mocked AzureOpenAIClient that returns a sample result."""
    client = MagicMock(spec=AzureOpenAIClient)
    client.generate.return_value = sample_generation_result
    client.deployment = "gpt-4o"
    return client
