"""GET /api/metrics — Aggregated compliance statistics.

Computes totals, rates, averages, flag breakdowns, and daily
time series from audit records over a configurable date range.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import azure.functions as func

from core.audit_logger import AuditStore, create_audit_store
from core.models import ErrorResponse, FlagBreakdown, MetricsResponse, TimeSeriesPoint

logger = logging.getLogger(__name__)

bp = func.Blueprint()

# Lazy-initialized singleton
_audit_store: Optional[AuditStore] = None


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


@bp.route(route="api/metrics", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.ANONYMOUS)
def metrics(req: func.HttpRequest) -> func.HttpResponse:
    """Return aggregated compliance metrics.

    Query parameters:
        date_from: Start date (YYYY-MM-DD). Default: 30 days ago.
        date_to: End date (YYYY-MM-DD). Default: today.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    date_from = req.params.get("date_from", thirty_days_ago)
    date_to = req.params.get("date_to", today)

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

    # Fetch all records in range (no status filter, large limit for aggregation)
    try:
        store = _get_audit_store()
        records, _total = store.list_records(
            date_from=date_from,
            date_to=date_to,
            limit=10000,
            offset=0,
        )
    except Exception as exc:
        logger.exception("Failed to retrieve audit records for metrics")
        error = ErrorResponse(
            error="internal_error",
            message=f"Failed to compute metrics: {exc}",
        )
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=500,
            mimetype="application/json",
        )

    # Single-pass O(n) aggregation
    total = len(records)
    if total == 0:
        response = MetricsResponse(
            date_from=date_from,
            date_to=date_to,
        )
        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    total_passed = 0
    total_failed = 0
    score_sum = 0.0
    duration_sum = 0.0
    flag_counts: dict[tuple[str, str], int] = defaultdict(int)
    daily: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "score_sum": 0.0})

    for record in records:
        # Counts
        if record.compliance_passed:
            total_passed += 1
        else:
            total_failed += 1

        # Sums for averages
        score_sum += record.compliance_score
        duration_sum += record.duration_ms

        # Flag breakdown
        for flag in record.compliance_flags:
            layer = flag.get("layer", "unknown")
            severity = flag.get("severity", "unknown")
            flag_counts[(layer, severity)] += 1

        # Daily time series
        date_key = record.timestamp[:10]
        day = daily[date_key]
        day["total"] += 1
        day["score_sum"] += record.compliance_score
        if record.compliance_passed:
            day["passed"] += 1
        else:
            day["failed"] += 1

    # Build response
    compliance_rate = round(total_passed / total, 4)
    avg_score = round(score_sum / total, 4)
    avg_duration = round(duration_sum / total, 2)

    flags_breakdown = [
        FlagBreakdown(layer=layer, severity=severity, count=count)
        for (layer, severity), count in sorted(flag_counts.items())
    ]

    time_series = [
        TimeSeriesPoint(
            date=date,
            total_requests=day["total"],
            passed=day["passed"],
            failed=day["failed"],
            avg_score=round(day["score_sum"] / day["total"], 4) if day["total"] > 0 else 0.0,
        )
        for date, day in sorted(daily.items())
    ]

    response = MetricsResponse(
        total_requests=total,
        total_passed=total_passed,
        total_failed=total_failed,
        compliance_rate=compliance_rate,
        avg_score=avg_score,
        avg_duration_ms=avg_duration,
        flags_breakdown=flags_breakdown,
        time_series=time_series,
        date_from=date_from,
        date_to=date_to,
    )

    return func.HttpResponse(
        body=response.model_dump_json(),
        status_code=200,
        mimetype="application/json",
    )
