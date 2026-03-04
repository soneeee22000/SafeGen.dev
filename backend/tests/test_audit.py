"""Tests for functions.audit — the GET /api/audit endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import azure.functions as func

from core.models import AuditRecord


def _make_record(
    request_id: str = "req001",
    compliance_passed: bool = True,
    compliance_score: float = 1.0,
) -> AuditRecord:
    """Create a test AuditRecord."""
    return AuditRecord(
        request_id=request_id,
        timestamp="2026-03-04T12:00:00Z",
        duration_ms=100,
        prompt="What is GDPR?",
        response_content="GDPR is a regulation.",
        model="gpt-4o",
        compliance_passed=compliance_passed,
        compliance_score=compliance_score,
        layers_run=["pii", "bias", "safety"],
    )


def _make_request(params: dict[str, str] | None = None) -> func.HttpRequest:
    """Create a mock GET HttpRequest with query params."""
    return func.HttpRequest(
        method="GET",
        url="/api/audit",
        params=params or {},
        body=b"",
    )


class TestAuditEndpoint:
    """Tests for the GET /api/audit endpoint."""

    @patch("functions.audit._get_audit_store")
    def test_returns_audit_records(self, mock_get_store: MagicMock) -> None:
        """Returns paginated audit records."""
        from functions.audit import audit

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([_make_record()], 1)
        mock_get_store.return_value = mock_store

        resp = audit(_make_request())
        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert data["total"] == 1
        assert len(data["records"]) == 1
        assert data["records"][0]["request_id"] == "req001"

    @patch("functions.audit._get_audit_store")
    def test_date_filter(self, mock_get_store: MagicMock) -> None:
        """Passes date_from and date_to to store."""
        from functions.audit import audit

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        req = _make_request({"date_from": "2026-03-01", "date_to": "2026-03-04"})
        audit(req)

        call_kwargs = mock_store.list_records.call_args[1]
        assert call_kwargs["date_from"] == "2026-03-01"
        assert call_kwargs["date_to"] == "2026-03-04"

    @patch("functions.audit._get_audit_store")
    def test_status_filter(self, mock_get_store: MagicMock) -> None:
        """Passes status filter to store."""
        from functions.audit import audit

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        req = _make_request({"status": "failed"})
        audit(req)

        call_kwargs = mock_store.list_records.call_args[1]
        assert call_kwargs["status"] == "failed"

    @patch("functions.audit._get_audit_store")
    def test_pagination_params(self, mock_get_store: MagicMock) -> None:
        """Passes limit and offset to store."""
        from functions.audit import audit

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        req = _make_request({"limit": "10", "offset": "5"})
        audit(req)

        call_kwargs = mock_store.list_records.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    @patch("functions.audit._get_audit_store")
    def test_invalid_date_returns_400(self, mock_get_store: MagicMock) -> None:
        """Invalid date format returns 400."""
        from functions.audit import audit

        req = _make_request({"date_from": "not-a-date"})
        resp = audit(req)

        assert resp.status_code == 400
        data = json.loads(resp.get_body())
        assert data["error"] == "invalid_parameters"

    @patch("functions.audit._get_audit_store")
    def test_invalid_status_returns_400(self, mock_get_store: MagicMock) -> None:
        """Invalid status value returns 400."""
        from functions.audit import audit

        req = _make_request({"status": "unknown"})
        resp = audit(req)

        assert resp.status_code == 400
        data = json.loads(resp.get_body())
        assert data["error"] == "invalid_parameters"

    @patch("functions.audit._get_audit_store")
    def test_default_date_range(self, mock_get_store: MagicMock) -> None:
        """Without date params, defaults to last 7 days."""
        from functions.audit import audit

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        audit(_make_request())

        call_kwargs = mock_store.list_records.call_args[1]
        # date_from should be 7 days before date_to
        assert "date_from" in call_kwargs
        assert "date_to" in call_kwargs

    @patch("functions.audit._get_audit_store")
    def test_store_error_returns_500(self, mock_get_store: MagicMock) -> None:
        """Store failure returns 500."""
        from functions.audit import audit

        mock_store = MagicMock()
        mock_store.list_records.side_effect = Exception("disk full")
        mock_get_store.return_value = mock_store

        resp = audit(_make_request())
        assert resp.status_code == 500
