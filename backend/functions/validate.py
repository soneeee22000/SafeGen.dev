"""POST /api/validate — Main compliance validation endpoint.

Proxies prompt to Azure OpenAI, then runs the compliance engine
against the LLM response. Returns the response with compliance
validation results (score, flags, pass/fail).
"""

from __future__ import annotations

import logging
import time
import uuid

import azure.functions as func
from pydantic import ValidationError

from core.audit_logger import AuditStore, create_audit_store
from core.compliance_engine import ComplianceEngine
from core.models import AuditRecord, ErrorResponse, ValidateRequest, ValidateResponse
from core.openai_client import AzureOpenAIClient

logger = logging.getLogger(__name__)

bp = func.Blueprint()

# Lazy-initialized singletons (cold start optimization)
_openai_client: AzureOpenAIClient | None = None
_compliance_engine: ComplianceEngine | None = None
_audit_store: AuditStore | None = None


def _get_openai_client() -> AzureOpenAIClient:
    """Get or create the Azure OpenAI client singleton."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAIClient()
    return _openai_client


def _get_compliance_engine() -> ComplianceEngine:
    """Get or create the compliance engine singleton."""
    global _compliance_engine
    if _compliance_engine is None:
        _compliance_engine = ComplianceEngine()
    return _compliance_engine


def _get_audit_store() -> AuditStore:
    """Get or create the audit store singleton."""
    global _audit_store
    if _audit_store is None:
        _audit_store = create_audit_store()
    return _audit_store


@bp.route(route="api/validate", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.ANONYMOUS)
def validate(req: func.HttpRequest) -> func.HttpResponse:
    """Validate a prompt through the compliance pipeline.

    Accepts a JSON body with prompt, optional context, and rules_category.
    Returns the LLM response with compliance validation results.

    Phase 1: Returns raw LLM response (no compliance checks yet).
    """
    request_id = uuid.uuid4().hex
    start_time = time.monotonic()

    # Parse and validate request body
    try:
        body = req.get_json()
    except ValueError:
        error = ErrorResponse(error="invalid_json", message="Request body must be valid JSON")
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=400,
            mimetype="application/json",
        )

    try:
        request = ValidateRequest(**body)
    except ValidationError as exc:
        error = ErrorResponse(
            error="validation_error",
            message="Invalid request payload",
            details={"errors": exc.errors()},
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=422,
            mimetype="application/json",
        )

    # Call Azure OpenAI
    try:
        client = _get_openai_client()
        result = client.generate(
            prompt=request.prompt,
            context=request.context,
        )
    except ValueError as exc:
        error = ErrorResponse(
            error="configuration_error",
            message=str(exc),
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=500,
            mimetype="application/json",
        )
    except Exception as exc:
        logger.exception("Azure OpenAI call failed")
        error = ErrorResponse(
            error="openai_error",
            message=f"Azure OpenAI request failed: {exc}",
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=502,
            mimetype="application/json",
        )

    # Run compliance engine against LLM response
    engine = _get_compliance_engine()
    compliance_result = engine.validate(
        text=result.content,
        rules_category=request.rules_category,
    )

    response = ValidateResponse(
        response=result.content,
        raw_response=result.content,
        compliance=compliance_result,
        model=result.model,
        usage=result.usage,
    )

    # Audit logging (fire-and-forget, non-fatal)
    try:
        from datetime import datetime, timezone

        duration_ms = int((time.monotonic() - start_time) * 1000)
        audit_record = AuditRecord(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            prompt=request.prompt[:500],
            rules_category=request.rules_category.value,
            response_content=result.content[:1000],
            model=result.model,
            usage=result.usage,
            compliance_passed=compliance_result.passed,
            compliance_score=compliance_result.score,
            compliance_flags=[f.model_dump() for f in compliance_result.flags],
            layers_run=compliance_result.layers_run,
        )
        _get_audit_store().save(audit_record)
    except Exception:
        logger.warning("Audit logging failed for request %s", request_id, exc_info=True)

    logger.info(
        "Validate request processed: request_id=%s, model=%s, compliance_passed=%s, score=%.2f",
        request_id,
        result.model,
        compliance_result.passed,
        compliance_result.score,
    )

    return func.HttpResponse(
        body=response.model_dump_json(),
        status_code=200,
        mimetype="application/json",
    )
