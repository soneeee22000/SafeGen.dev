"""Azure Blob Storage client for SafeGen.

Handles upload, download, list, and delete operations for
compliance rule documents and audit logs.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlobMetadata:
    """Metadata for a stored blob."""

    name: str
    container: str
    url: str
    size: int
    content_type: str
    created_on: Optional[datetime] = None
    metadata: dict | None = None


class BlobStorageClient:
    """Wrapper around Azure Blob Storage for SafeGen."""

    def __init__(self, connection_string: Optional[str] = None) -> None:
        """Initialize the Blob Storage client.

        Args:
            connection_string: Azure Storage connection string. Falls back to env var.
        """
        self._connection_string = connection_string or os.environ.get(
            "AZURE_STORAGE_CONNECTION_STRING", ""
        )
        if not self._connection_string:
            raise ValueError(
                "Azure Storage connection string is required. "
                "Set AZURE_STORAGE_CONNECTION_STRING environment variable."
            )
        self._service_client = BlobServiceClient.from_connection_string(
            self._connection_string
        )

    def _ensure_container(self, container_name: str) -> None:
        """Create the container if it does not exist.

        Args:
            container_name: Name of the blob container.
        """
        container_client = self._service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
            logger.info("Created container: %s", container_name)

    def upload(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> BlobMetadata:
        """Upload a blob to Azure Blob Storage.

        Args:
            container_name: Target container name.
            blob_name: Name for the blob.
            data: Raw bytes to upload.
            content_type: MIME type of the blob.
            metadata: Optional key-value metadata to attach.

        Returns:
            BlobMetadata with upload details.
        """
        self._ensure_container(container_name)
        blob_client = self._service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        content_settings = ContentSettings(content_type=content_type)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=content_settings,
            metadata=metadata,
        )

        logger.info("Uploaded blob: %s/%s (%d bytes)", container_name, blob_name, len(data))

        return BlobMetadata(
            name=blob_name,
            container=container_name,
            url=blob_client.url,
            size=len(data),
            content_type=content_type,
            metadata=metadata,
        )

    def download(self, container_name: str, blob_name: str) -> bytes:
        """Download a blob's content.

        Args:
            container_name: Container name.
            blob_name: Blob name.

        Returns:
            Raw bytes of the blob content.
        """
        blob_client = self._service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        downloader = blob_client.download_blob()
        data = downloader.readall()
        logger.info("Downloaded blob: %s/%s (%d bytes)", container_name, blob_name, len(data))
        return data

    def list_blobs(
        self,
        container_name: str,
        prefix: Optional[str] = None,
    ) -> list[BlobMetadata]:
        """List all blobs in a container.

        Args:
            container_name: Container name.
            prefix: Optional prefix filter.

        Returns:
            List of BlobMetadata for each blob.
        """
        self._ensure_container(container_name)
        container_client = self._service_client.get_container_client(container_name)
        blobs = container_client.list_blobs(name_starts_with=prefix)

        results = []
        for blob in blobs:
            results.append(
                BlobMetadata(
                    name=blob.name,
                    container=container_name,
                    url=f"{container_client.url}/{blob.name}",
                    size=blob.size,
                    content_type=blob.content_settings.content_type if blob.content_settings else "",
                    created_on=blob.creation_time,
                    metadata=blob.metadata,
                )
            )
        return results

    def delete(self, container_name: str, blob_name: str) -> None:
        """Delete a blob.

        Args:
            container_name: Container name.
            blob_name: Blob name.
        """
        blob_client = self._service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        blob_client.delete_blob()
        logger.info("Deleted blob: %s/%s", container_name, blob_name)
