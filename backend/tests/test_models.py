"""Tests for core.models — Pydantic request/response validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
    ComplianceResult,
    ErrorResponse,
    RulesCategory,
    ValidateRequest,
    ValidateResponse,
    ValidationFlag,
)


class TestValidateRequest:
    """Tests for ValidateRequest model."""

    def test_valid_minimal_request(self) -> None:
        """Minimal request with just a prompt."""
        req = ValidateRequest(prompt="What is compliance?")
        assert req.prompt == "What is compliance?"
        assert req.context is None
        assert req.rules_category == RulesCategory.ALL
        assert req.stream is False

    def test_valid_full_request(self) -> None:
        """Request with all fields populated."""
        req = ValidateRequest(
            prompt="Explain GDPR",
            context="European data protection regulation",
            rules_category=RulesCategory.REGULATORY,
            stream=True,
        )
        assert req.prompt == "Explain GDPR"
        assert req.context == "European data protection regulation"
        assert req.rules_category == RulesCategory.REGULATORY
        assert req.stream is True

    def test_empty_prompt_rejected(self) -> None:
        """Empty prompt should fail validation."""
        with pytest.raises(ValidationError):
            ValidateRequest(prompt="")

    def test_prompt_too_long_rejected(self) -> None:
        """Prompt exceeding max_length should fail."""
        with pytest.raises(ValidationError):
            ValidateRequest(prompt="x" * 10001)

    def test_invalid_rules_category_rejected(self) -> None:
        """Invalid rules category should fail."""
        with pytest.raises(ValidationError):
            ValidateRequest(prompt="test", rules_category="invalid")


class TestValidateResponse:
    """Tests for ValidateResponse model."""

    def test_response_without_compliance(self) -> None:
        """Phase 1 response has no compliance result."""
        resp = ValidateResponse(
            response="Here is a safe answer.",
            model="gpt-4o",
        )
        assert resp.response == "Here is a safe answer."
        assert resp.compliance is None
        assert resp.raw_response is None

    def test_response_with_compliance(self) -> None:
        """Phase 3 response includes compliance result."""
        compliance = ComplianceResult(
            passed=True,
            score=0.95,
            flags=[],
            layers_run=["pii", "bias", "safety", "compliance"],
        )
        resp = ValidateResponse(
            response="Safe answer.",
            raw_response="Original answer.",
            compliance=compliance,
            model="gpt-4o",
            usage={"total_tokens": 100},
        )
        assert resp.compliance.passed is True
        assert resp.compliance.score == 0.95
        assert resp.raw_response == "Original answer."


class TestComplianceResult:
    """Tests for ComplianceResult model."""

    def test_passing_result(self) -> None:
        """A clean compliance result with no flags."""
        result = ComplianceResult(passed=True, score=1.0)
        assert result.passed is True
        assert result.flags == []

    def test_failing_result_with_flags(self) -> None:
        """A failing result with multiple flags."""
        flags = [
            ValidationFlag(layer="pii", severity="critical", message="Email detected in response"),
            ValidationFlag(layer="bias", severity="warning", message="Gendered language detected"),
        ]
        result = ComplianceResult(
            passed=False,
            score=0.3,
            flags=flags,
            layers_run=["pii", "bias"],
        )
        assert result.passed is False
        assert len(result.flags) == 2
        assert result.flags[0].severity == "critical"

    def test_score_boundaries(self) -> None:
        """Score must be between 0.0 and 1.0."""
        ComplianceResult(passed=True, score=0.0)
        ComplianceResult(passed=True, score=1.0)
        with pytest.raises(ValidationError):
            ComplianceResult(passed=True, score=-0.1)
        with pytest.raises(ValidationError):
            ComplianceResult(passed=True, score=1.1)


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_minimal_error(self) -> None:
        """Error with required fields only."""
        err = ErrorResponse(error="not_found", message="Resource not found")
        assert err.error == "not_found"
        assert err.details is None

    def test_error_with_details(self) -> None:
        """Error with additional context."""
        err = ErrorResponse(
            error="validation_error",
            message="Bad input",
            details={"field": "prompt", "issue": "too_long"},
        )
        assert err.details["field"] == "prompt"
