"""POST /api/validate — Main compliance validation endpoint.

Phase 1: Proxies prompt to Azure OpenAI and returns the response.
Phase 3: Adds compliance engine validation before returning.
"""

from __future__ import annotations

import logging

import azure.functions as func
from pydantic import ValidationError

from core.models import ErrorResponse, ValidateRequest, ValidateResponse
from core.openai_client import AzureOpenAIClient

logger = logging.getLogger(__name__)

bp = func.Blueprint()

# Lazy-initialized client (cold start optimization)
_openai_client: AzureOpenAIClient | None = None


def _get_openai_client() -> AzureOpenAIClient:
    """Get or create the Azure OpenAI client singleton."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAIClient()
    return _openai_client


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

    # Phase 1: Return raw response without compliance validation
    # Phase 3 will add: compliance_result = compliance_engine.validate(result.content)
    response = ValidateResponse(
        response=result.content,
        raw_response=None,  # Same as response in Phase 1 (no modification)
        compliance=None,  # Phase 3 will populate this
        model=result.model,
        usage=result.usage,
    )

    logger.info("Validate request processed successfully, model=%s", result.model)

    return func.HttpResponse(
        body=response.model_dump_json(),
        status_code=200,
        mimetype="application/json",
    )
