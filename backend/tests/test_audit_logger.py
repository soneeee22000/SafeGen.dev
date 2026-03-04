"""Tests for core.audit_logger — AuditStore implementations and factory."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.audit_logger import BlobAuditStore, FileAuditStore, create_audit_store
from core.models import AuditRecord


def _make_record(
    request_id: str = "req001",
    timestamp: str = "2026-03-04T12:00:00Z",
    compliance_passed: bool = True,
    compliance_score: float = 1.0,
) -> AuditRecord:
    """Create a test AuditRecord."""
    return AuditRecord(
        request_id=request_id,
        timestamp=timestamp,
        duration_ms=100,
        prompt="What is GDPR?",
        rules_category="all",
        response_content="GDPR is a regulation.",
        model="gpt-4o",
        usage={"total_tokens": 70},
        compliance_passed=compliance_passed,
        compliance_score=compliance_score,
        compliance_flags=[],
        layers_run=["pii", "bias", "safety"],
    )


class TestFileAuditStore:
    """Tests for FileAuditStore."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() writes a JSON file under {date}/{request_id}.json."""
        store = FileAuditStore(base_dir=str(tmp_path))
        record = _make_record()
        store.save(record)

        expected_path = tmp_path / "2026-03-04" / "req001.json"
        assert expected_path.exists()
        data = json.loads(expected_path.read_text(encoding="utf-8"))
        assert data["request_id"] == "req001"

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        """save() overwrites if the same request_id is saved again."""
        store = FileAuditStore(base_dir=str(tmp_path))
        record = _make_record(compliance_score=0.5)
        store.save(record)

        updated = _make_record(compliance_score=0.9)
        store.save(updated)

        path = tmp_path / "2026-03-04" / "req001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["compliance_score"] == 0.9

    def test_list_records_returns_saved(self, tmp_path: Path) -> None:
        """list_records() returns records within the date range."""
        store = FileAuditStore(base_dir=str(tmp_path))
        store.save(_make_record(request_id="r1", timestamp="2026-03-01T10:00:00Z"))
        store.save(_make_record(request_id="r2", timestamp="2026-03-02T10:00:00Z"))
        store.save(_make_record(request_id="r3", timestamp="2026-03-03T10:00:00Z"))

        records, total = store.list_records(date_from="2026-03-01", date_to="2026-03-03")
        assert total == 3
        assert len(records) == 3

    def test_list_records_date_filter(self, tmp_path: Path) -> None:
        """list_records() filters by date range."""
        store = FileAuditStore(base_dir=str(tmp_path))
        store.save(_make_record(request_id="r1", timestamp="2026-03-01T10:00:00Z"))
        store.save(_make_record(request_id="r2", timestamp="2026-03-03T10:00:00Z"))

        records, total = store.list_records(date_from="2026-03-02", date_to="2026-03-03")
        assert total == 1
        assert records[0].request_id == "r2"

    def test_list_records_status_filter_passed(self, tmp_path: Path) -> None:
        """list_records() filters by compliance_passed=True."""
        store = FileAuditStore(base_dir=str(tmp_path))
        store.save(_make_record(request_id="pass1", compliance_passed=True))
        store.save(_make_record(request_id="fail1", compliance_passed=False, compliance_score=0.3))

        records, total = store.list_records(date_from="2026-03-04", date_to="2026-03-04", status="passed")
        assert total == 1
        assert records[0].request_id == "pass1"

    def test_list_records_status_filter_failed(self, tmp_path: Path) -> None:
        """list_records() filters by compliance_passed=False."""
        store = FileAuditStore(base_dir=str(tmp_path))
        store.save(_make_record(request_id="pass1", compliance_passed=True))
        store.save(_make_record(request_id="fail1", compliance_passed=False, compliance_score=0.3))

        records, total = store.list_records(date_from="2026-03-04", date_to="2026-03-04", status="failed")
        assert total == 1
        assert records[0].request_id == "fail1"

    def test_list_records_pagination(self, tmp_path: Path) -> None:
        """list_records() respects limit and offset."""
        store = FileAuditStore(base_dir=str(tmp_path))
        for i in range(5):
            store.save(_make_record(request_id=f"r{i:03d}"))

        records, total = store.list_records(date_from="2026-03-04", date_to="2026-03-04", limit=2, offset=1)
        assert total == 5
        assert len(records) == 2

    def test_list_records_empty_store(self, tmp_path: Path) -> None:
        """list_records() returns empty when no records exist."""
        store = FileAuditStore(base_dir=str(tmp_path))
        records, total = store.list_records(date_from="2026-03-04", date_to="2026-03-04")
        assert total == 0
        assert records == []

    def test_list_records_skips_corrupt_files(self, tmp_path: Path) -> None:
        """list_records() skips files that can't be parsed as AuditRecord."""
        store = FileAuditStore(base_dir=str(tmp_path))
        store.save(_make_record(request_id="good"))

        # Write a corrupt file
        date_dir = tmp_path / "2026-03-04"
        (date_dir / "corrupt.json").write_text("not valid json", encoding="utf-8")

        records, total = store.list_records(date_from="2026-03-04", date_to="2026-03-04")
        assert total == 1
        assert records[0].request_id == "good"

    def test_list_records_sorted_by_timestamp(self, tmp_path: Path) -> None:
        """list_records() returns records sorted by timestamp descending."""
        store = FileAuditStore(base_dir=str(tmp_path))
        store.save(_make_record(request_id="early", timestamp="2026-03-04T08:00:00Z"))
        store.save(_make_record(request_id="late", timestamp="2026-03-04T20:00:00Z"))

        records, _ = store.list_records(date_from="2026-03-04", date_to="2026-03-04")
        assert records[0].request_id == "late"
        assert records[1].request_id == "early"


class TestBlobAuditStore:
    """Tests for BlobAuditStore (mocked blob client)."""

    def test_save_uploads_json(self) -> None:
        """save() uploads JSON to blob storage."""
        mock_client = MagicMock()
        store = BlobAuditStore(blob_client=mock_client, container_name="audit-logs")
        record = _make_record()

        store.save(record)

        mock_client.upload.assert_called_once()
        call_kwargs = mock_client.upload.call_args
        assert call_kwargs[1]["container_name"] == "audit-logs"
        assert "2026-03-04/req001.json" in call_kwargs[1]["blob_name"]
        assert call_kwargs[1]["content_type"] == "application/json"


class TestCreateAuditStore:
    """Tests for the factory function."""

    def test_returns_file_store_without_connection_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without AZURE_STORAGE_CONNECTION_STRING, returns FileAuditStore."""
        monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
        store = create_audit_store()
        assert isinstance(store, FileAuditStore)

    def test_returns_blob_store_with_connection_string(self, mock_env: None) -> None:
        """With AZURE_STORAGE_CONNECTION_STRING, returns BlobAuditStore."""
        with patch("core.audit_logger.BlobStorageClient"):
            store = create_audit_store()
            assert isinstance(store, BlobAuditStore)
