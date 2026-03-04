"""GET /api/audit — Paginated audit log retrieval.

Returns audit records with date-range, status filtering, and pagination.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import azure.functions as func

from core.audit_logger import AuditStore, create_audit_store
from core.models import AuditListResponse, ErrorResponse

logger = logging.getLogger(__name__)

bp = func.Blueprint()

# Lazy-initialized singleton
_audit_store: Optional[AuditStore] = None

_VALID_STATUSES = {"passed", "failed"}


def _get_audit_store() -> AuditStore:
    """Get or create the audit store singleton."""
    global _audit_store
    if _audit_store is None:
        _audit_store = create_audit_store()
    return _audit_store


def _validate_date(date_str: str) -> bool:
    """Check if a string is a valid YYYY-MM-DD date."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


@bp.route(route="api/audit", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.ANONYMOUS)
def audit(req: func.HttpRequest) -> func.HttpResponse:
    """Retrieve paginated audit records.

    Query parameters:
        date_from: Start date (YYYY-MM-DD). Default: 7 days ago.
        date_to: End date (YYYY-MM-DD). Default: today.
        status: "passed" | "failed". Default: all.
        limit: Page size (1-200). Default: 50.
        offset: Skip count. Default: 0.
    """
    # Parse and validate query parameters
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    date_from = req.params.get("date_from", seven_days_ago)
    date_to = req.params.get("date_to", today)
    status = req.params.get("status")
    limit_str = req.params.get("limit", "50")
    offset_str = req.params.get("offset", "0")

    # Validate dates
    if not _validate_date(date_from) or not _validate_date(date_to):
        error = ErrorResponse(
            error="invalid_parameters",
            message="date_from and date_to must be in YYYY-MM-DD format",
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=400,
            mimetype="application/json",
        )

    # Validate status
    if status is not None and status not in _VALID_STATUSES:
        error = ErrorResponse(
            error="invalid_parameters",
            message=f"status must be one of: {', '.join(_VALID_STATUSES)}",
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=400,
            mimetype="application/json",
        )

    # Parse limit/offset
    try:
        limit = max(1, min(200, int(limit_str)))
        offset = max(0, int(offset_str))
    except ValueError:
        limit = 50
        offset = 0

    # Query the store
    try:
        store = _get_audit_store()
        records, total = store.list_records(
            date_from=date_from,
            date_to=date_to,
            status=status,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception("Failed to retrieve audit records")
        error = ErrorResponse(
            error="internal_error",
            message=f"Failed to retrieve audit records: {exc}",
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=500,
            mimetype="application/json",
        )

    response = AuditListResponse(
        records=records,
        total=total,
        limit=limit,
        offset=offset,
    )

    return func.HttpResponse(
        body=response.model_dump_json(),
        status_code=200,
        mimetype="application/json",
    )
