"""Azure OpenAI client wrapper for SafeGen."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

logger = logging.getLogger(__name__)

# Default system prompt for the compliance-aware assistant
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Respond accurately and concisely. "
    "Do not generate harmful, biased, or personally identifiable information. "
    "If you are unsure about something, say so rather than guessing."
)


@dataclass(frozen=True)
class GenerationResult:
    """Result from an Azure OpenAI generation call."""

    content: str
    model: str
    usage: dict
    finish_reason: str


class AzureOpenAIClient:
    """Wrapper around the Azure OpenAI API for SafeGen."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        """Initialize the Azure OpenAI client.

        Args:
            endpoint: Azure OpenAI endpoint URL. Falls back to env var.
            api_key: Azure OpenAI API key. Falls back to env var.
            deployment: Model deployment name. Falls back to env var.
            api_version: API version string. Falls back to env var.
        """
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY", "")
        self.deployment = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")

        if not self.endpoint or not self.api_key:
            raise ValueError(
                "Azure OpenAI endpoint and API key are required. "
                "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables."
            )

        self._client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> GenerationResult:
        """Generate a response from Azure OpenAI.

        Args:
            prompt: The user's prompt.
            context: Optional additional context prepended to the prompt.
            system_prompt: Optional system prompt override.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            GenerationResult with content, model, usage, and finish_reason.

        Raises:
            openai.APIError: If the Azure OpenAI API call fails.
        """
        messages = [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
        ]

        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})

        logger.info(
            "Calling Azure OpenAI deployment=%s, prompt_length=%d",
            self.deployment,
            len(prompt),
        )

        response: ChatCompletion = self._client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = (
            {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            if response.usage
            else {}
        )

        logger.info(
            "Azure OpenAI response: model=%s, tokens=%s, finish_reason=%s",
            response.model,
            usage.get("total_tokens", "unknown"),
            choice.finish_reason,
        )

        return GenerationResult(
            content=choice.message.content or "",
            model=response.model or self.deployment,
            usage=usage,
            finish_reason=choice.finish_reason or "stop",
        )
