"""Tests for functions.validate — the /api/validate endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import azure.functions as func

from core.openai_client import GenerationResult


class TestValidateEndpoint:
    """Tests for the validate HTTP trigger function."""

    def _make_request(self, body: dict | str | None = None) -> func.HttpRequest:
        """Create a mock HttpRequest with JSON body."""
        if body is None:
            body_bytes = b""
        elif isinstance(body, str):
            body_bytes = body.encode()
        else:
            body_bytes = json.dumps(body).encode()

        return func.HttpRequest(
            method="POST",
            url="/api/validate",
            body=body_bytes,
            headers={"Content-Type": "application/json"},
        )

    def test_valid_request_returns_200(self, mock_env: None, sample_generation_result: GenerationResult) -> None:
        """Valid request with prompt returns 200 with LLM response and compliance."""
        import functions.validate as validate_module
        from functions.validate import validate

        mock_client = MagicMock()
        mock_client.generate.return_value = sample_generation_result

        # Inject mock client
        validate_module._openai_client = mock_client
        validate_module._compliance_engine = None

        req = self._make_request({"prompt": "What is GDPR?"})
        resp = validate(req)

        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert data["response"] == "This is a safe and helpful response."
        assert data["model"] == "gpt-4o"
        # Phase 3: compliance is now populated
        assert data["compliance"] is not None
        assert data["compliance"]["passed"] is True
        assert data["compliance"]["score"] >= 0.9
        assert "pii" in data["compliance"]["layers_run"]

        # Cleanup
        validate_module._openai_client = None
        validate_module._compliance_engine = None

    def test_invalid_json_returns_400(self) -> None:
        """Non-JSON body returns 400."""
        from functions.validate import validate

        req = func.HttpRequest(
            method="POST",
            url="/api/validate",
            body=b"not json",
            headers={"Content-Type": "application/json"},
        )
        resp = validate(req)

        assert resp.status_code == 400
        data = json.loads(resp.get_body())
        assert data["error"] == "invalid_json"

    def test_missing_prompt_returns_422(self) -> None:
        """Request without prompt field returns 422."""
        from functions.validate import validate

        req = self._make_request({"context": "some context"})
        resp = validate(req)

        assert resp.status_code == 422
        data = json.loads(resp.get_body())
        assert data["error"] == "validation_error"

    def test_empty_prompt_returns_422(self) -> None:
        """Empty prompt string returns 422."""
        from functions.validate import validate

        req = self._make_request({"prompt": ""})
        resp = validate(req)

        assert resp.status_code == 422

    def test_openai_failure_returns_502(self, mock_env: None) -> None:
        """Azure OpenAI API failure returns 502."""
        import functions.validate as validate_module
        from functions.validate import validate

        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("API timeout")

        validate_module._openai_client = mock_client

        req = self._make_request({"prompt": "test"})
        resp = validate(req)

        assert resp.status_code == 502
        data = json.loads(resp.get_body())
        assert data["error"] == "openai_error"
        assert "API timeout" in data["message"]

        validate_module._openai_client = None
        validate_module._compliance_engine = None

    def test_request_with_context_passes_to_client(
        self, mock_env: None, sample_generation_result: GenerationResult
    ) -> None:
        """Context field is forwarded to the OpenAI client."""
        import functions.validate as validate_module
        from functions.validate import validate

        mock_client = MagicMock()
        mock_client.generate.return_value = sample_generation_result

        validate_module._openai_client = mock_client
        validate_module._compliance_engine = None

        req = self._make_request({
            "prompt": "Summarize this",
            "context": "Document about GDPR compliance.",
        })
        resp = validate(req)

        assert resp.status_code == 200
        mock_client.generate.assert_called_once_with(
            prompt="Summarize this",
            context="Document about GDPR compliance.",
        )

        validate_module._openai_client = None
        validate_module._compliance_engine = None

    def test_response_includes_usage_stats(
        self, mock_env: None, sample_generation_result: GenerationResult
    ) -> None:
        """Response includes token usage statistics."""
        import functions.validate as validate_module
        from functions.validate import validate

        mock_client = MagicMock()
        mock_client.generate.return_value = sample_generation_result

        validate_module._openai_client = mock_client
        validate_module._compliance_engine = None

        req = self._make_request({"prompt": "test"})
        resp = validate(req)

        data = json.loads(resp.get_body())
        assert data["usage"]["total_tokens"] == 70

        validate_module._openai_client = None
        validate_module._compliance_engine = None

    def test_compliance_flags_pii_in_response(self, mock_env: None) -> None:
        """Response containing PII gets flagged by compliance engine."""
        import functions.validate as validate_module
        from functions.validate import validate

        pii_result = GenerationResult(
            content="Contact john.doe@realcompany.com for more details.",
            model="gpt-4o",
            usage={"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
            finish_reason="stop",
        )
        mock_client = MagicMock()
        mock_client.generate.return_value = pii_result

        validate_module._openai_client = mock_client
        validate_module._compliance_engine = None

        req = self._make_request({"prompt": "How do I contact support?"})
        resp = validate(req)

        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert data["compliance"]["passed"] is False
        assert any(f["layer"] == "pii" for f in data["compliance"]["flags"])

        validate_module._openai_client = None
        validate_module._compliance_engine = None

    def test_compliance_respects_rules_category(self, mock_env: None) -> None:
        """rules_category=pii only runs PII validator, not bias."""
        import functions.validate as validate_module
        from functions.validate import validate

        # Response has bias ("chairman") but request only checks PII
        bias_result = GenerationResult(
            content="The chairman announced the new policy.",
            model="gpt-4o",
            usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            finish_reason="stop",
        )
        mock_client = MagicMock()
        mock_client.generate.return_value = bias_result

        validate_module._openai_client = mock_client
        validate_module._compliance_engine = None

        req = self._make_request({"prompt": "What happened?", "rules_category": "pii"})
        resp = validate(req)

        data = json.loads(resp.get_body())
        assert "pii" in data["compliance"]["layers_run"]
        assert "bias" not in data["compliance"]["layers_run"]
        # No PII in text, so should pass even though bias exists
        assert data["compliance"]["passed"] is True

        validate_module._openai_client = None
        validate_module._compliance_engine = None
