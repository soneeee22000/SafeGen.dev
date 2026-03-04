"""POST /api/validate — Main compliance validation endpoint.

Proxies prompt to Azure OpenAI, then runs the compliance engine
against the LLM response. Returns the response with compliance
validation results (score, flags, pass/fail).
"""

from __future__ import annotations

import logging

import azure.functions as func
from pydantic import ValidationError

from core.compliance_engine import ComplianceEngine
from core.models import ErrorResponse, ValidateRequest, ValidateResponse
from core.openai_client import AzureOpenAIClient

logger = logging.getLogger(__name__)

bp = func.Blueprint()

# Lazy-initialized singletons (cold start optimization)
_openai_client: AzureOpenAIClient | None = None
_compliance_engine: ComplianceEngine | None = None


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


@bp.route(route="api/validate", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.ANONYMOUS)
def validate(req: func.HttpRequest) -> func.HttpResponse:
    """Validate a prompt through the compliance pipeline.

    Accepts a JSON body with prompt, optional context, and rules_category.
    Returns the LLM response with compliance validation results.

    Phase 1: Returns raw LLM response (no compliance checks yet).
    """
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

    logger.info(
        "Validate request processed: model=%s, compliance_passed=%s, score=%.2f",
        result.model,
        compliance_result.passed,
        compliance_result.score,
    )

    return func.HttpResponse(
        body=response.model_dump_json(),
        status_code=200,
        mimetype="application/json",
    )
