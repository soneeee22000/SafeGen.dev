"""Audit logging for SafeGen — persists every validation request.

Dual-backend architecture:
- FileAuditStore: writes JSON to disk (local dev)
- BlobAuditStore: writes to Azure Blob Storage (production)
- create_audit_store(): factory that auto-selects the backend
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional, Protocol

from core.blob_storage import BlobStorageClient
from core.models import AuditRecord

logger = logging.getLogger(__name__)

# Default local audit directory (relative to backend/)
_DEFAULT_AUDIT_DIR = "audit_data"


class AuditStore(Protocol):
    """Protocol for audit record persistence."""

    def save(self, record: AuditRecord) -> None:
        """Persist a single audit record."""
        ...

    def list_records(
        self,
        date_from: str,
        date_to: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        """Retrieve audit records within a date range.

        Args:
            date_from: Start date (YYYY-MM-DD), inclusive.
            date_to: End date (YYYY-MM-DD), inclusive.
            status: Filter by "passed" or "failed". None for all.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            Tuple of (records, total_count).
        """
        ...


class FileAuditStore:
    """File-based audit store for local development.

    Writes audit records as JSON files organized by date:
    {base_dir}/{YYYY-MM-DD}/{request_id}.json
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        """Initialize with a base directory for audit files.

        Args:
            base_dir: Root directory for audit files. Defaults to audit_data/.
        """
        self.base_dir = Path(base_dir) if base_dir else Path(_DEFAULT_AUDIT_DIR)

    def save(self, record: AuditRecord) -> None:
        """Write an audit record to disk as JSON.

        Args:
            record: The audit record to persist.
        """
        date_str = record.timestamp[:10]
        date_dir = self.base_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        file_path = date_dir / f"{record.request_id}.json"
        file_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        logger.debug("Audit record saved: %s", file_path)

    def list_records(
        self,
        date_from: str,
        date_to: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        """Read audit records from disk within the date range.

        Args:
            date_from: Start date (YYYY-MM-DD), inclusive.
            date_to: End date (YYYY-MM-DD), inclusive.
            status: Filter by "passed" or "failed". None for all.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            Tuple of (paginated records, total matching count).
        """
        all_records: list[AuditRecord] = []

        if not self.base_dir.exists():
            return [], 0

        for date_dir in sorted(self.base_dir.iterdir()):
            if not date_dir.is_dir():
                continue

            dir_date = date_dir.name
            if dir_date < date_from or dir_date > date_to:
                continue

            for json_file in date_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    record = AuditRecord(**data)
                    all_records.append(record)
                except (json.JSONDecodeError, Exception):
                    logger.warning("Skipping corrupt audit file: %s", json_file)
                    continue

        # Filter by status
        if status == "passed":
            all_records = [r for r in all_records if r.compliance_passed]
        elif status == "failed":
            all_records = [r for r in all_records if not r.compliance_passed]

        # Sort by timestamp descending (newest first)
        all_records.sort(key=lambda r: r.timestamp, reverse=True)

        total = len(all_records)
        paginated = all_records[offset : offset + limit]

        return paginated, total


class BlobAuditStore:
    """Azure Blob Storage-backed audit store for production.

    Stores audit records as JSON blobs organized by date:
    audit/{YYYY-MM-DD}/{request_id}.json
    """

    def __init__(
        self,
        blob_client: Optional[BlobStorageClient] = None,
        container_name: Optional[str] = None,
    ) -> None:
        """Initialize with a blob storage client.

        Args:
            blob_client: BlobStorageClient instance. Created from env vars if None.
            container_name: Container name. Defaults to AZURE_STORAGE_CONTAINER_AUDIT env var.
        """
        self._client = blob_client or BlobStorageClient()
        self._container = container_name or os.environ.get("AZURE_STORAGE_CONTAINER_AUDIT", "audit-logs")

    def save(self, record: AuditRecord) -> None:
        """Upload an audit record to blob storage.

        Args:
            record: The audit record to persist.
        """
        date_str = record.timestamp[:10]
        blob_name = f"audit/{date_str}/{record.request_id}.json"
        data = record.model_dump_json(indent=2).encode("utf-8")

        self._client.upload(
            container_name=self._container,
            blob_name=blob_name,
            data=data,
            content_type="application/json",
        )
        logger.debug("Audit record uploaded: %s/%s", self._container, blob_name)

    def list_records(
        self,
        date_from: str,
        date_to: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        """List audit records from blob storage within the date range.

        Args:
            date_from: Start date (YYYY-MM-DD), inclusive.
            date_to: End date (YYYY-MM-DD), inclusive.
            status: Filter by "passed" or "failed". None for all.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            Tuple of (paginated records, total matching count).
        """
        all_records: list[AuditRecord] = []

        blobs = self._client.list_blobs(container_name=self._container, prefix="audit/")

        for blob in blobs:
            # Extract date from blob name: audit/YYYY-MM-DD/request_id.json
            parts = blob.name.split("/")
            if len(parts) < 3:
                continue

            blob_date = parts[1]
            if blob_date < date_from or blob_date > date_to:
                continue

            try:
                data = self._client.download(container_name=self._container, blob_name=blob.name)
                parsed = json.loads(data.decode("utf-8"))
                record = AuditRecord(**parsed)
                all_records.append(record)
            except Exception:
                logger.warning("Skipping corrupt audit blob: %s", blob.name)
                continue

        # Filter by status
        if status == "passed":
            all_records = [r for r in all_records if r.compliance_passed]
        elif status == "failed":
            all_records = [r for r in all_records if not r.compliance_passed]

        # Sort by timestamp descending
        all_records.sort(key=lambda r: r.timestamp, reverse=True)

        total = len(all_records)
        paginated = all_records[offset : offset + limit]

        return paginated, total


def create_audit_store() -> AuditStore:
    """Factory function to create the appropriate audit store.

    Returns BlobAuditStore if AZURE_STORAGE_CONNECTION_STRING is set,
    otherwise returns FileAuditStore for local development.

    Returns:
        An AuditStore implementation.
    """
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    if connection_string:
        logger.info("Using BlobAuditStore (Azure Blob Storage)")
        return BlobAuditStore()

    logger.info("Using FileAuditStore (local filesystem)")
    return FileAuditStore()
