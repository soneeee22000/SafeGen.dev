"""Pydantic models for SafeGen request/response contracts."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RulesCategory(str, Enum):
    """Categories of compliance rules for targeted validation."""

    SAFETY = "safety"
    BIAS = "bias"
    PII = "pii"
    REGULATORY = "regulatory"
    ALL = "all"


class ValidateRequest(BaseModel):
    """Request payload for the /api/validate endpoint."""

    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt to send to LLM")
    context: Optional[str] = Field(None, max_length=20000, description="Additional context for the LLM")
    rules_category: RulesCategory = Field(
        default=RulesCategory.ALL,
        description="Which compliance rule category to validate against",
    )
    stream: bool = Field(default=False, description="Whether to stream the response")


class ValidationFlag(BaseModel):
    """A single compliance flag raised during validation."""

    layer: str = Field(..., description="Validation layer: pii | bias | safety | compliance")
    severity: str = Field(default="warning", description="Severity: info | warning | critical")
    message: str = Field(..., description="Human-readable flag description")
    details: dict = Field(default_factory=dict, description="Layer-specific metadata")


class ComplianceResult(BaseModel):
    """Aggregate compliance validation result."""

    passed: bool = Field(..., description="Whether the response passed all compliance checks")
    score: float = Field(..., ge=0.0, le=1.0, description="Overall compliance score (0.0 to 1.0)")
    flags: list[ValidationFlag] = Field(default_factory=list, description="List of raised flags")
    layers_run: list[str] = Field(default_factory=list, description="Which validation layers were executed")


class ValidateResponse(BaseModel):
    """Response payload from the /api/validate endpoint."""

    response: str = Field(..., description="LLM-generated response (validated)")
    raw_response: Optional[str] = Field(None, description="Original LLM response before validation")
    compliance: Optional[ComplianceResult] = Field(
        None,
        description="Compliance validation result (None if validation is disabled)",
    )
    model: str = Field(..., description="Model deployment name used")
    usage: Optional[dict] = Field(None, description="Token usage statistics")


class AuditRecord(BaseModel):
    """A single audit log entry for a validation request."""

    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    duration_ms: int = Field(default=0, ge=0, description="Processing time in milliseconds")
    prompt: str = Field(..., description="User prompt (truncated to 500 chars)")
    rules_category: str = Field(default="all", description="Compliance rule category used")
    response_content: str = Field(..., description="LLM response (truncated to 1000 chars)")
    model: str = Field(..., description="Model deployment name")
    usage: Optional[dict] = Field(None, description="Token usage statistics")
    compliance_passed: bool = Field(..., description="Whether compliance checks passed")
    compliance_score: float = Field(..., ge=0.0, le=1.0, description="Compliance score")
    compliance_flags: list[dict] = Field(default_factory=list, description="Serialized ValidationFlags")
    layers_run: list[str] = Field(default_factory=list, description="Validation layers executed")


class AuditListResponse(BaseModel):
    """Paginated list of audit records."""

    records: list[AuditRecord] = Field(default_factory=list, description="Audit records")
    total: int = Field(default=0, ge=0, description="Total matching records")
    limit: int = Field(default=50, ge=1, le=200, description="Page size")
    offset: int = Field(default=0, ge=0, description="Page offset")


class TimeSeriesPoint(BaseModel):
    """A single data point in a time series."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    total_requests: int = Field(default=0, ge=0, description="Total requests on this date")
    passed: int = Field(default=0, ge=0, description="Passed requests")
    failed: int = Field(default=0, ge=0, description="Failed requests")
    avg_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Average compliance score")


class FlagBreakdown(BaseModel):
    """Count of flags by layer and severity."""

    layer: str = Field(..., description="Validation layer name")
    severity: str = Field(..., description="Flag severity level")
    count: int = Field(default=0, ge=0, description="Number of flags")


class MetricsResponse(BaseModel):
    """Aggregated compliance metrics over a date range."""

    total_requests: int = Field(default=0, ge=0, description="Total validation requests")
    total_passed: int = Field(default=0, ge=0, description="Requests that passed compliance")
    total_failed: int = Field(default=0, ge=0, description="Requests that failed compliance")
    compliance_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Pass rate")
    avg_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Average compliance score")
    avg_duration_ms: float = Field(default=0.0, ge=0.0, description="Average processing time")
    flags_breakdown: list[FlagBreakdown] = Field(default_factory=list, description="Flag counts by layer/severity")
    time_series: list[TimeSeriesPoint] = Field(default_factory=list, description="Daily request counts")
    date_from: str = Field(..., description="Start date (YYYY-MM-DD)")
    date_to: str = Field(..., description="End date (YYYY-MM-DD)")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")
