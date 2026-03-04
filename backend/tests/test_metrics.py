"""Tests for functions.metrics — the GET /api/metrics endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import azure.functions as func

from core.models import AuditRecord


def _make_record(
    request_id: str = "req001",
    timestamp: str = "2026-03-04T12:00:00Z",
    compliance_passed: bool = True,
    compliance_score: float = 1.0,
    duration_ms: int = 100,
    compliance_flags: list[dict] | None = None,
    layers_run: list[str] | None = None,
) -> AuditRecord:
    """Create a test AuditRecord."""
    return AuditRecord(
        request_id=request_id,
        timestamp=timestamp,
        duration_ms=duration_ms,
        prompt="What is GDPR?",
        response_content="GDPR is a regulation.",
        model="gpt-4o",
        compliance_passed=compliance_passed,
        compliance_score=compliance_score,
        compliance_flags=compliance_flags or [],
        layers_run=layers_run or ["pii", "bias", "safety"],
    )


def _make_request(params: dict[str, str] | None = None) -> func.HttpRequest:
    """Create a mock GET HttpRequest."""
    return func.HttpRequest(
        method="GET",
        url="/api/metrics",
        params=params or {},
        body=b"",
    )


class TestMetricsEndpoint:
    """Tests for the GET /api/metrics endpoint."""

    @patch("functions.metrics._get_audit_store")
    def test_counts_and_rates(self, mock_get_store: MagicMock) -> None:
        """Computes total, passed, failed, and compliance_rate."""
        from functions.metrics import metrics

        records = [
            _make_record(request_id="r1", compliance_passed=True, compliance_score=1.0),
            _make_record(request_id="r2", compliance_passed=True, compliance_score=0.9),
            _make_record(request_id="r3", compliance_passed=False, compliance_score=0.3),
        ]
        mock_store = MagicMock()
        mock_store.list_records.return_value = (records, 3)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-03-04", "date_to": "2026-03-04"}))
        data = json.loads(resp.get_body())

        assert data["total_requests"] == 3
        assert data["total_passed"] == 2
        assert data["total_failed"] == 1
        assert abs(data["compliance_rate"] - 2 / 3) < 0.01

    @patch("functions.metrics._get_audit_store")
    def test_avg_score(self, mock_get_store: MagicMock) -> None:
        """Computes average compliance score."""
        from functions.metrics import metrics

        records = [
            _make_record(request_id="r1", compliance_score=1.0),
            _make_record(request_id="r2", compliance_score=0.8),
        ]
        mock_store = MagicMock()
        mock_store.list_records.return_value = (records, 2)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-03-04", "date_to": "2026-03-04"}))
        data = json.loads(resp.get_body())
        assert abs(data["avg_score"] - 0.9) < 0.01

    @patch("functions.metrics._get_audit_store")
    def test_avg_duration(self, mock_get_store: MagicMock) -> None:
        """Computes average duration_ms."""
        from functions.metrics import metrics

        records = [
            _make_record(request_id="r1", duration_ms=100),
            _make_record(request_id="r2", duration_ms=200),
        ]
        mock_store = MagicMock()
        mock_store.list_records.return_value = (records, 2)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-03-04", "date_to": "2026-03-04"}))
        data = json.loads(resp.get_body())
        assert abs(data["avg_duration_ms"] - 150.0) < 0.01

    @patch("functions.metrics._get_audit_store")
    def test_flags_breakdown(self, mock_get_store: MagicMock) -> None:
        """Aggregates flags by layer and severity."""
        from functions.metrics import metrics

        records = [
            _make_record(
                request_id="r1",
                compliance_flags=[
                    {"layer": "pii", "severity": "critical", "message": "Email found"},
                    {"layer": "bias", "severity": "warning", "message": "Gendered term"},
                ],
            ),
            _make_record(
                request_id="r2",
                compliance_flags=[
                    {"layer": "pii", "severity": "critical", "message": "Phone found"},
                ],
            ),
        ]
        mock_store = MagicMock()
        mock_store.list_records.return_value = (records, 2)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-03-04", "date_to": "2026-03-04"}))
        data = json.loads(resp.get_body())

        breakdown = {(fb["layer"], fb["severity"]): fb["count"] for fb in data["flags_breakdown"]}
        assert breakdown[("pii", "critical")] == 2
        assert breakdown[("bias", "warning")] == 1

    @patch("functions.metrics._get_audit_store")
    def test_time_series(self, mock_get_store: MagicMock) -> None:
        """Generates daily time series data."""
        from functions.metrics import metrics

        records = [
            _make_record(
                request_id="r1", timestamp="2026-03-01T10:00:00Z", compliance_passed=True, compliance_score=1.0
            ),
            _make_record(
                request_id="r2", timestamp="2026-03-01T15:00:00Z", compliance_passed=False, compliance_score=0.5
            ),
            _make_record(
                request_id="r3", timestamp="2026-03-02T10:00:00Z", compliance_passed=True, compliance_score=0.9
            ),
        ]
        mock_store = MagicMock()
        mock_store.list_records.return_value = (records, 3)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-03-01", "date_to": "2026-03-02"}))
        data = json.loads(resp.get_body())

        ts = {p["date"]: p for p in data["time_series"]}
        assert ts["2026-03-01"]["total_requests"] == 2
        assert ts["2026-03-01"]["passed"] == 1
        assert ts["2026-03-01"]["failed"] == 1
        assert ts["2026-03-02"]["total_requests"] == 1

    @patch("functions.metrics._get_audit_store")
    def test_empty_records(self, mock_get_store: MagicMock) -> None:
        """Empty records return zero metrics."""
        from functions.metrics import metrics

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-03-04", "date_to": "2026-03-04"}))
        data = json.loads(resp.get_body())

        assert data["total_requests"] == 0
        assert data["compliance_rate"] == 0.0
        assert data["avg_score"] == 0.0
        assert data["time_series"] == []

    @patch("functions.metrics._get_audit_store")
    def test_date_range_in_response(self, mock_get_store: MagicMock) -> None:
        """date_from and date_to are included in the response."""
        from functions.metrics import metrics

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request({"date_from": "2026-02-01", "date_to": "2026-03-04"}))
        data = json.loads(resp.get_body())

        assert data["date_from"] == "2026-02-01"
        assert data["date_to"] == "2026-03-04"

    @patch("functions.metrics._get_audit_store")
    def test_invalid_date_returns_400(self, mock_get_store: MagicMock) -> None:
        """Invalid date format returns 400."""
        from functions.metrics import metrics

        resp = metrics(_make_request({"date_from": "bad-date"}))
        assert resp.status_code == 400

    @patch("functions.metrics._get_audit_store")
    def test_default_date_range(self, mock_get_store: MagicMock) -> None:
        """Without date params, defaults to last 30 days."""
        from functions.metrics import metrics

        mock_store = MagicMock()
        mock_store.list_records.return_value = ([], 0)
        mock_get_store.return_value = mock_store

        metrics(_make_request())

        call_kwargs = mock_store.list_records.call_args[1]
        assert "date_from" in call_kwargs
        assert "date_to" in call_kwargs

    @patch("functions.metrics._get_audit_store")
    def test_store_error_returns_500(self, mock_get_store: MagicMock) -> None:
        """Store failure returns 500."""
        from functions.metrics import metrics

        mock_store = MagicMock()
        mock_store.list_records.side_effect = Exception("connection lost")
        mock_get_store.return_value = mock_store

        resp = metrics(_make_request())
        assert resp.status_code == 500
