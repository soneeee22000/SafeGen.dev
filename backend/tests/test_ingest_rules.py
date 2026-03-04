"""Tests for functions.ingest_rules — rule document ingestion endpoint."""

from __future__ import annotations

import json
import tempfile

import azure.functions as func


class TestIngestRulesEndpoint:
    """Tests for the /api/rules/ingest endpoint."""

    def _make_json_request(self, body: dict) -> func.HttpRequest:
        """Create a JSON POST request."""
        return func.HttpRequest(
            method="POST",
            url="/api/rules/ingest",
            body=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )

    def test_ingest_json_content(self, mock_env: None, tmp_path: str) -> None:
        """Ingesting plain text content via JSON creates chunks and indexes them."""
        import functions.ingest_rules as module

        # Use temp directory for FAISS index
        with tempfile.TemporaryDirectory() as tmpdir:
            module.FAISS_INDEX_DIR = tmpdir
            module._faiss_index = None

            req = self._make_json_request(
                {
                    "content": "AI must not generate biased content. All outputs must be reviewed for fairness and accuracy.",
                    "filename": "bias_rules.md",
                }
            )

            resp = module.ingest_rules(req)
            assert resp.status_code == 201

            data = json.loads(resp.get_body())
            assert data["filename"] == "bias_rules.md"
            assert data["chunk_count"] >= 1
            assert data["status"] == "indexed"
            assert "rule_id" in data

            # Cleanup
            module._faiss_index = None

    def test_ingest_empty_content_returns_400(self, mock_env: None) -> None:
        """Empty content field returns 400."""
        import functions.ingest_rules as module

        module._faiss_index = None

        req = self._make_json_request({"content": "", "filename": "empty.md"})
        resp = module.ingest_rules(req)
        assert resp.status_code == 400

        data = json.loads(resp.get_body())
        assert data["error"] == "empty_content"

        module._faiss_index = None

    def test_ingest_invalid_json_returns_400(self) -> None:
        """Invalid JSON body returns 400."""
        import functions.ingest_rules as module

        req = func.HttpRequest(
            method="POST",
            url="/api/rules/ingest",
            body=b"not json",
            headers={"Content-Type": "application/json"},
        )
        resp = module.ingest_rules(req)
        assert resp.status_code == 400

    def test_ingest_multiple_rules_accumulates(self, mock_env: None) -> None:
        """Ingesting multiple rules accumulates in the same index."""
        import functions.ingest_rules as module

        with tempfile.TemporaryDirectory() as tmpdir:
            module.FAISS_INDEX_DIR = tmpdir
            module._faiss_index = None

            # First rule
            req1 = self._make_json_request(
                {
                    "content": "GDPR requires data minimization and purpose limitation.",
                    "filename": "gdpr.md",
                }
            )
            resp1 = module.ingest_rules(req1)
            data1 = json.loads(resp1.get_body())

            # Second rule
            req2 = self._make_json_request(
                {
                    "content": "PII must be masked in all AI outputs including emails and phone numbers.",
                    "filename": "pii.md",
                }
            )
            resp2 = module.ingest_rules(req2)
            data2 = json.loads(resp2.get_body())

            # Second ingestion should have more total vectors
            assert data2["total_index_size"] > data1["total_index_size"]

            module._faiss_index = None
