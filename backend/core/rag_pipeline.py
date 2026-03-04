"""RAG pipeline for SafeGen — document processing, embedding, and retrieval.

Handles:
1. Text extraction from PDF, DOCX, Markdown, and plain text files
2. Text chunking with configurable size and overlap
3. Embedding generation via Hugging Face sentence-transformers
4. FAISS vector index management (add, search, persist, load)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 500  # tokens (approximate by words)
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5


# ── Data Models ────────────────────────────────────────────────────────────────


@dataclass
class DocumentChunk:
    """A chunk of text extracted from a document."""

    content: str
    chunk_index: int
    source_file: str
    page_number: Optional[int] = None
    token_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single result from a FAISS similarity search."""

    chunk: DocumentChunk
    score: float
    rank: int


# ── Text Extraction ───────────────────────────────────────────────────────────


def extract_text_from_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    """Extract text from a PDF file, returning (page_number, text) tuples.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        List of (page_number, page_text) tuples (1-indexed pages).
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append((page_num + 1, text.strip()))
    doc.close()
    logger.info("Extracted %d pages from PDF", len(pages))
    return pages


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file.

    Args:
        file_bytes: Raw bytes of the DOCX file.

    Returns:
        Full text content of the document.
    """
    import io

    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    logger.info("Extracted %d paragraphs from DOCX", len(paragraphs))
    return text


def extract_text(file_bytes: bytes, filename: str) -> list[tuple[Optional[int], str]]:
    """Extract text from a file based on its extension.

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used to detect type).

    Returns:
        List of (page_number_or_none, text) tuples.

    Raises:
        ValueError: If the file type is not supported.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        text = extract_text_from_docx(file_bytes)
        return [(None, text)]
    elif ext in (".md", ".txt", ".markdown"):
        text = file_bytes.decode("utf-8", errors="replace")
        return [(None, text)]
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .docx, .md, .txt")


# ── Text Chunking ─────────────────────────────────────────────────────────────


def chunk_text(
    text: str,
    source_file: str,
    page_number: Optional[int] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Split text into overlapping chunks.

    Uses word-based splitting as an approximation of token count.

    Args:
        text: Full text to chunk.
        source_file: Name of the source file.
        page_number: Optional page number for citation tracking.
        chunk_size: Target chunk size in words.
        chunk_overlap: Number of overlapping words between chunks.

    Returns:
        List of DocumentChunk objects.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        content = " ".join(chunk_words)

        chunks.append(
            DocumentChunk(
                content=content,
                chunk_index=chunk_index,
                source_file=source_file,
                page_number=page_number,
                token_count=len(chunk_words),
            )
        )

        chunk_index += 1
        start += chunk_size - chunk_overlap

        # Avoid creating tiny trailing chunks
        if start < len(words) and len(words) - start < chunk_overlap:
            break

    logger.info("Chunked '%s' into %d chunks", source_file, len(chunks))
    return chunks


def chunk_document(
    file_bytes: bytes,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Extract text from a document and chunk it.

    Args:
        file_bytes: Raw file content.
        filename: Original filename.
        chunk_size: Target chunk size in words.
        chunk_overlap: Overlap between chunks.

    Returns:
        List of DocumentChunk objects from the entire document.
    """
    pages = extract_text(file_bytes, filename)
    all_chunks = []

    for page_num, text in pages:
        chunks = chunk_text(
            text=text,
            source_file=filename,
            page_number=page_num,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(chunks)

    # Re-index chunks sequentially across pages
    for i, chunk in enumerate(all_chunks):
        chunk.chunk_index = i

    return all_chunks


# ── Embedding ──────────────────────────────────────────────────────────────────

# Lazy-loaded model to avoid slow imports at startup
_embedding_model = None


def _get_embedding_model(model_name: Optional[str] = None):
    """Get or load the sentence-transformer embedding model.

    Args:
        model_name: HuggingFace model name. Defaults to env var or all-MiniLM-L6-v2.

    Returns:
        SentenceTransformer model instance.
    """
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        name = model_name or os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        logger.info("Loading embedding model: %s", name)
        _embedding_model = SentenceTransformer(name)
    return _embedding_model


def generate_embeddings(
    texts: list[str],
    model_name: Optional[str] = None,
) -> np.ndarray:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.
        model_name: Optional model name override.

    Returns:
        numpy array of shape (len(texts), embedding_dim).
    """
    model = _get_embedding_model(model_name)
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    logger.info("Generated %d embeddings, dim=%d", len(texts), embeddings.shape[1])
    return embeddings


# ── FAISS Index ────────────────────────────────────────────────────────────────


class FAISSIndex:
    """FAISS vector index for semantic search over document chunks.

    Manages the FAISS index alongside a parallel list of DocumentChunk
    metadata for result reconstruction.
    """

    def __init__(self, dimension: int = 384) -> None:
        """Initialize an empty FAISS index.

        Args:
            dimension: Embedding vector dimension. Default 384 for all-MiniLM-L6-v2.
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine after normalization)
        self.chunks: list[DocumentChunk] = []

    @property
    def size(self) -> int:
        """Number of vectors in the index."""
        return self.index.ntotal

    def add(self, chunks: list[DocumentChunk], embeddings: np.ndarray) -> None:
        """Add document chunks and their embeddings to the index.

        Args:
            chunks: List of DocumentChunk objects.
            embeddings: numpy array of shape (len(chunks), dimension).

        Raises:
            ValueError: If chunks and embeddings lengths don't match.
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({embeddings.shape[0]}) must have same length")

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.chunks.extend(chunks)

        logger.info("Added %d vectors to FAISS index (total: %d)", len(chunks), self.size)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[SearchResult]:
        """Search the index for the most similar chunks.

        Args:
            query_embedding: Query vector of shape (1, dimension) or (dimension,).
            top_k: Number of results to return.

        Returns:
            List of SearchResult objects sorted by relevance.
        """
        if self.size == 0:
            logger.warning("Search called on empty FAISS index")
            return []

        # Reshape if needed
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Normalize query for cosine similarity
        faiss.normalize_L2(query_embedding)

        k = min(top_k, self.size)
        scores, indices = self.index.search(query_embedding, k)

        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0], strict=True)):
            if idx < 0:  # FAISS returns -1 for missing results
                continue
            results.append(
                SearchResult(
                    chunk=self.chunks[idx],
                    score=float(score),
                    rank=rank,
                )
            )

        logger.info(
            "FAISS search returned %d results (top score: %.4f)", len(results), results[0].score if results else 0.0
        )
        return results

    def save(self, directory: str) -> None:
        """Persist the FAISS index and chunk metadata to disk.

        Args:
            directory: Directory path to save index files.
        """
        os.makedirs(directory, exist_ok=True)
        index_path = os.path.join(directory, "index.faiss")
        meta_path = os.path.join(directory, "chunks.json")

        faiss.write_index(self.index, index_path)

        chunks_data = [
            {
                "content": c.content,
                "chunk_index": c.chunk_index,
                "source_file": c.source_file,
                "page_number": c.page_number,
                "token_count": c.token_count,
                "metadata": c.metadata,
            }
            for c in self.chunks
        ]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)

        logger.info("Saved FAISS index (%d vectors) to %s", self.size, directory)

    @classmethod
    def load(cls, directory: str) -> FAISSIndex:
        """Load a FAISS index and chunk metadata from disk.

        Args:
            directory: Directory path containing saved index files.

        Returns:
            FAISSIndex instance with loaded data.

        Raises:
            FileNotFoundError: If index files are not found.
        """
        index_path = os.path.join(directory, "index.faiss")
        meta_path = os.path.join(directory, "chunks.json")

        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            raise FileNotFoundError(f"FAISS index files not found in {directory}")

        index = faiss.read_index(index_path)

        with open(meta_path, encoding="utf-8") as f:
            chunks_data = json.load(f)

        chunks = [
            DocumentChunk(
                content=c["content"],
                chunk_index=c["chunk_index"],
                source_file=c["source_file"],
                page_number=c.get("page_number"),
                token_count=c.get("token_count", 0),
                metadata=c.get("metadata", {}),
            )
            for c in chunks_data
        ]

        instance = cls(dimension=index.d)
        instance.index = index
        instance.chunks = chunks

        logger.info("Loaded FAISS index (%d vectors) from %s", instance.size, directory)
        return instance
