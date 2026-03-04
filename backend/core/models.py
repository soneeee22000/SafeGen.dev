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


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")
