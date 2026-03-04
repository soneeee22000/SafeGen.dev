"""POST /api/rules/ingest — Upload and index compliance rule documents.

Accepts a file upload (PDF, DOCX, MD, TXT), extracts text, chunks it,
generates embeddings, and adds to the FAISS index for RAG retrieval.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

import azure.functions as func

from core.rag_pipeline import (
    FAISSIndex,
    chunk_document,
    generate_embeddings,
)

logger = logging.getLogger(__name__)

bp = func.Blueprint()

# Shared FAISS index — persisted to disk between invocations
FAISS_INDEX_DIR = os.environ.get("FAISS_INDEX_DIR", "./faiss_index")
_faiss_index: FAISSIndex | None = None


def _get_faiss_index() -> FAISSIndex:
    """Get or load the shared FAISS index."""
    global _faiss_index
    if _faiss_index is None:
        try:
            _faiss_index = FAISSIndex.load(FAISS_INDEX_DIR)
            logger.info("Loaded existing FAISS index with %d vectors", _faiss_index.size)
        except FileNotFoundError:
            _faiss_index = FAISSIndex(dimension=384)
            logger.info("Created new empty FAISS index")
    return _faiss_index


@bp.route(
    route="api/rules/ingest",
    methods=[func.HttpMethod.POST],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def ingest_rules(req: func.HttpRequest) -> func.HttpResponse:
    """Ingest a compliance rule document into the RAG pipeline.

    Accepts multipart/form-data with a file field named 'file'.
    Alternatively accepts JSON with 'content' and 'filename' fields
    for plain text rules.
    """
    content_type = req.headers.get("Content-Type", "")

    # Handle JSON body (plain text rules)
    if "application/json" in content_type:
        return _ingest_from_json(req)

    # Handle file upload
    try:
        file = req.files.get("file")
        if file is None:
            return func.HttpResponse(
                body=json.dumps({"error": "missing_file", "message": "No file provided. Upload a file with field name 'file'."}),
                status_code=400,
                mimetype="application/json",
            )

        filename = file.filename or f"rule_{uuid.uuid4().hex[:8]}.txt"
        file_bytes = file.read()

        if not file_bytes:
            return func.HttpResponse(
                body=json.dumps({"error": "empty_file", "message": "Uploaded file is empty."}),
                status_code=400,
                mimetype="application/json",
            )

        return _process_and_index(file_bytes, filename)

    except Exception as exc:
        logger.exception("Rule ingestion failed")
        return func.HttpResponse(
            body=json.dumps({"error": "ingestion_error", "message": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )


def _ingest_from_json(req: func.HttpRequest) -> func.HttpResponse:
    """Handle JSON-based rule ingestion for plain text content."""
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            body=json.dumps({"error": "invalid_json", "message": "Request body must be valid JSON."}),
            status_code=400,
            mimetype="application/json",
        )

    content = body.get("content", "")
    filename = body.get("filename", f"rule_{uuid.uuid4().hex[:8]}.md")

    if not content.strip():
        return func.HttpResponse(
            body=json.dumps({"error": "empty_content", "message": "Content field is required and cannot be empty."}),
            status_code=400,
            mimetype="application/json",
        )

    file_bytes = content.encode("utf-8")
    return _process_and_index(file_bytes, filename)


def _process_and_index(file_bytes: bytes, filename: str) -> func.HttpResponse:
    """Extract text, chunk, embed, and add to FAISS index.

    Args:
        file_bytes: Raw file content.
        filename: Original filename.

    Returns:
        HTTP response with ingestion results.
    """
    rule_id = uuid.uuid4().hex[:12]

    # Chunk the document
    chunks = chunk_document(file_bytes, filename)
    if not chunks:
        return func.HttpResponse(
            body=json.dumps({"error": "no_content", "message": "No text could be extracted from the file."}),
            status_code=400,
            mimetype="application/json",
        )

    # Tag chunks with rule_id for tracking
    for chunk in chunks:
        chunk.metadata["rule_id"] = rule_id

    # Generate embeddings
    texts = [chunk.content for chunk in chunks]
    embeddings = generate_embeddings(texts)

    # Add to FAISS index
    index = _get_faiss_index()
    index.add(chunks, embeddings)

    # Persist index to disk
    index.save(FAISS_INDEX_DIR)

    result = {
        "rule_id": rule_id,
        "filename": filename,
        "chunk_count": len(chunks),
        "total_index_size": index.size,
        "status": "indexed",
    }

    logger.info("Ingested rule '%s': %d chunks, rule_id=%s", filename, len(chunks), rule_id)

    return func.HttpResponse(
        body=json.dumps(result),
        status_code=201,
        mimetype="application/json",
    )
