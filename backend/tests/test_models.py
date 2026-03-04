"""Tests for core.models — Pydantic request/response validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
    AuditListResponse,
    AuditRecord,
    ComplianceResult,
    ErrorResponse,
    FlagBreakdown,
    MetricsResponse,
    RulesCategory,
    TimeSeriesPoint,
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


class TestAuditRecord:
    """Tests for AuditRecord model."""

    def test_valid_audit_record(self) -> None:
        """Minimal valid audit record."""
        record = AuditRecord(
            request_id="abc123",
            timestamp="2026-03-04T12:00:00Z",
            prompt="What is GDPR?",
            response_content="GDPR is a regulation.",
            model="gpt-4o",
            compliance_passed=True,
            compliance_score=1.0,
        )
        assert record.request_id == "abc123"
        assert record.duration_ms == 0
        assert record.rules_category == "all"
        assert record.compliance_flags == []

    def test_full_audit_record(self) -> None:
        """Audit record with all fields populated."""
        record = AuditRecord(
            request_id="def456",
            timestamp="2026-03-04T12:00:00Z",
            duration_ms=150,
            prompt="Check this text",
            rules_category="pii",
            response_content="Some response",
            model="gpt-4o",
            usage={"total_tokens": 100},
            compliance_passed=False,
            compliance_score=0.7,
            compliance_flags=[{"layer": "pii", "severity": "critical", "message": "Email found"}],
            layers_run=["pii"],
        )
        assert record.duration_ms == 150
        assert record.compliance_passed is False
        assert len(record.compliance_flags) == 1

    def test_negative_duration_rejected(self) -> None:
        """Negative duration_ms should fail validation."""
        with pytest.raises(ValidationError):
            AuditRecord(
                request_id="x",
                timestamp="2026-03-04T12:00:00Z",
                duration_ms=-1,
                prompt="test",
                response_content="resp",
                model="gpt-4o",
                compliance_passed=True,
                compliance_score=1.0,
            )

    def test_score_boundaries(self) -> None:
        """Compliance score must be 0.0 to 1.0."""
        with pytest.raises(ValidationError):
            AuditRecord(
                request_id="x",
                timestamp="t",
                prompt="p",
                response_content="r",
                model="m",
                compliance_passed=True,
                compliance_score=1.5,
            )


class TestAuditListResponse:
    """Tests for AuditListResponse model."""

    def test_empty_list(self) -> None:
        """Empty audit list response."""
        resp = AuditListResponse()
        assert resp.records == []
        assert resp.total == 0
        assert resp.limit == 50
        assert resp.offset == 0

    def test_limit_boundaries(self) -> None:
        """Limit must be 1-200."""
        with pytest.raises(ValidationError):
            AuditListResponse(limit=0)
        with pytest.raises(ValidationError):
            AuditListResponse(limit=201)


class TestTimeSeriesPoint:
    """Tests for TimeSeriesPoint model."""

    def test_valid_point(self) -> None:
        """Valid time series data point."""
        point = TimeSeriesPoint(date="2026-03-04", total_requests=10, passed=8, failed=2, avg_score=0.85)
        assert point.date == "2026-03-04"
        assert point.total_requests == 10


class TestFlagBreakdown:
    """Tests for FlagBreakdown model."""

    def test_valid_breakdown(self) -> None:
        """Valid flag breakdown entry."""
        fb = FlagBreakdown(layer="pii", severity="critical", count=5)
        assert fb.layer == "pii"
        assert fb.count == 5


class TestMetricsResponse:
    """Tests for MetricsResponse model."""

    def test_empty_metrics(self) -> None:
        """Metrics with no data."""
        metrics = MetricsResponse(date_from="2026-03-01", date_to="2026-03-04")
        assert metrics.total_requests == 0
        assert metrics.compliance_rate == 0.0
        assert metrics.flags_breakdown == []
        assert metrics.time_series == []

    def test_full_metrics(self) -> None:
        """Metrics with all fields populated."""
        metrics = MetricsResponse(
            total_requests=100,
            total_passed=90,
            total_failed=10,
            compliance_rate=0.9,
            avg_score=0.85,
            avg_duration_ms=120.5,
            flags_breakdown=[FlagBreakdown(layer="pii", severity="critical", count=10)],
            time_series=[TimeSeriesPoint(date="2026-03-04", total_requests=50, passed=45, failed=5, avg_score=0.88)],
            date_from="2026-03-01",
            date_to="2026-03-04",
        )
        assert metrics.total_passed == 90
        assert len(metrics.flags_breakdown) == 1
        assert len(metrics.time_series) == 1
