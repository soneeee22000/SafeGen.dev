"""GET /api/rules — List all indexed compliance rules."""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict

import azure.functions as func

from core.rag_pipeline import FAISSIndex

logger = logging.getLogger(__name__)

bp = func.Blueprint()

FAISS_INDEX_DIR = os.environ.get("FAISS_INDEX_DIR", "./faiss_index")


@bp.route(
    route="api/rules",
    methods=[func.HttpMethod.GET],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def list_rules(req: func.HttpRequest) -> func.HttpResponse:
    """List all compliance rules currently in the FAISS index.

    Returns a summary grouped by source file, including chunk counts
    and rule IDs.
    """
    try:
        index = FAISSIndex.load(FAISS_INDEX_DIR)
    except FileNotFoundError:
        return func.HttpResponse(
            body=json.dumps({"rules": [], "total_chunks": 0, "total_rules": 0}),
            status_code=200,
            mimetype="application/json",
        )

    # Group chunks by source file
    rules_by_file: dict[str, dict] = defaultdict(
        lambda: {"filename": "", "rule_id": "", "chunk_count": 0, "sample_content": ""}
    )

    for chunk in index.chunks:
        key = chunk.source_file
        entry = rules_by_file[key]
        entry["filename"] = chunk.source_file
        entry["rule_id"] = chunk.metadata.get("rule_id", "unknown")
        entry["chunk_count"] += 1
        if not entry["sample_content"] and chunk.content:
            # First 200 chars as preview
            entry["sample_content"] = chunk.content[:200] + ("..." if len(chunk.content) > 200 else "")

    rules_list = list(rules_by_file.values())

    result = {
        "rules": rules_list,
        "total_chunks": index.size,
        "total_rules": len(rules_list),
    }

    return func.HttpResponse(
        body=json.dumps(result),
        status_code=200,
        mimetype="application/json",
    )
