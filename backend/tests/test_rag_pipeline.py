"""Tests for core.rag_pipeline — text extraction, chunking, embedding, FAISS."""

from __future__ import annotations

import tempfile

import numpy as np
import pytest

from core.rag_pipeline import (
    DocumentChunk,
    FAISSIndex,
    SearchResult,
    chunk_document,
    chunk_text,
    extract_text,
    generate_embeddings,
)

# ── Text Extraction Tests ────────────────────────────────────────────────────


class TestExtractText:
    """Tests for text extraction from various file types."""

    def test_extract_markdown(self) -> None:
        """Extract text from a Markdown file."""
        content = b"# Title\n\nSome content here.\n\n## Section\n\nMore content."
        pages = extract_text(content, "rules.md")
        assert len(pages) == 1
        assert pages[0][0] is None  # No page number for MD
        assert "Title" in pages[0][1]

    def test_extract_plain_text(self) -> None:
        """Extract text from a plain text file."""
        content = b"Plain text compliance rule content."
        pages = extract_text(content, "rules.txt")
        assert len(pages) == 1
        assert "Plain text" in pages[0][1]

    def test_unsupported_format_raises(self) -> None:
        """Unsupported file extension raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(b"data", "file.xlsx")


# ── Chunking Tests ───────────────────────────────────────────────────────────


class TestChunkText:
    """Tests for text chunking logic."""

    def test_short_text_single_chunk(self) -> None:
        """Text shorter than chunk_size produces a single chunk."""
        text = "Hello world this is a short text"
        chunks = chunk_text(text, "test.md", chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].source_file == "test.md"
        assert chunks[0].chunk_index == 0

    def test_long_text_multiple_chunks(self) -> None:
        """Long text is split into multiple overlapping chunks."""
        # 100 words
        words = [f"word{i}" for i in range(100)]
        text = " ".join(words)
        chunks = chunk_text(text, "test.md", chunk_size=30, chunk_overlap=5)
        assert len(chunks) > 1

        # Each chunk should have roughly chunk_size words (except last)
        for chunk in chunks[:-1]:
            assert chunk.token_count == 30

    def test_overlap_works(self) -> None:
        """Consecutive chunks share overlapping words."""
        words = [f"w{i}" for i in range(50)]
        text = " ".join(words)
        chunks = chunk_text(text, "test.md", chunk_size=20, chunk_overlap=5)

        # Get words from first two chunks
        words_1 = set(chunks[0].content.split())
        words_2 = set(chunks[1].content.split())
        overlap = words_1 & words_2
        assert len(overlap) >= 5

    def test_empty_text_returns_empty(self) -> None:
        """Empty text produces no chunks."""
        chunks = chunk_text("", "test.md")
        assert chunks == []

    def test_page_number_preserved(self) -> None:
        """Page number is carried through to chunks."""
        chunks = chunk_text("Some content here", "test.pdf", page_number=3)
        assert all(c.page_number == 3 for c in chunks)


class TestChunkDocument:
    """Tests for the full document chunking pipeline."""

    def test_chunk_markdown_file(self) -> None:
        """Chunk a Markdown file end-to-end."""
        content = "# GDPR Rules\n\n" + " ".join(f"word{i}" for i in range(200))
        chunks = chunk_document(content.encode(), "gdpr.md", chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 1
        assert chunks[0].source_file == "gdpr.md"
        # Indices should be sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


# ── Embedding Tests ──────────────────────────────────────────────────────────


class TestGenerateEmbeddings:
    """Tests for embedding generation."""

    def test_embeddings_shape(self) -> None:
        """Embeddings have correct shape (n_texts, dimension)."""
        texts = ["Hello world", "Compliance is important", "Safety first"]
        embeddings = generate_embeddings(texts)
        assert embeddings.shape[0] == 3
        assert embeddings.shape[1] == 384  # all-MiniLM-L6-v2 dimension

    def test_single_text_embedding(self) -> None:
        """Single text produces (1, dim) array."""
        embeddings = generate_embeddings(["Test"])
        assert embeddings.shape[0] == 1

    def test_similar_texts_closer(self) -> None:
        """Semantically similar texts have higher cosine similarity."""
        texts = [
            "GDPR data protection regulation",
            "European privacy law compliance",
            "Chocolate cake recipe ingredients",
        ]
        embeddings = generate_embeddings(texts)

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms

        # Similarity between first two (both about data protection)
        sim_related = float(np.dot(normalized[0], normalized[1]))
        # Similarity between first and third (unrelated)
        sim_unrelated = float(np.dot(normalized[0], normalized[2]))

        assert sim_related > sim_unrelated


# ── FAISS Index Tests ────────────────────────────────────────────────────────


class TestFAISSIndex:
    """Tests for FAISS vector index operations."""

    def _make_chunks_and_embeddings(self, n: int = 5, dim: int = 384) -> tuple[list[DocumentChunk], np.ndarray]:
        """Create test chunks and random embeddings."""
        chunks = [
            DocumentChunk(
                content=f"Chunk {i} about compliance rule {i}",
                chunk_index=i,
                source_file="test.md",
                metadata={"rule_id": f"rule_{i}"},
            )
            for i in range(n)
        ]
        embeddings = np.random.randn(n, dim).astype(np.float32)
        return chunks, embeddings

    def test_empty_index(self) -> None:
        """New index has size 0."""
        index = FAISSIndex()
        assert index.size == 0

    def test_add_vectors(self) -> None:
        """Adding chunks increases index size."""
        index = FAISSIndex()
        chunks, embeddings = self._make_chunks_and_embeddings(5)
        index.add(chunks, embeddings)
        assert index.size == 5

    def test_add_mismatched_raises(self) -> None:
        """Mismatched chunks and embeddings raises ValueError."""
        index = FAISSIndex()
        chunks, _ = self._make_chunks_and_embeddings(3)
        bad_embeddings = np.random.randn(5, 384).astype(np.float32)
        with pytest.raises(ValueError, match="same length"):
            index.add(chunks, bad_embeddings)

    def test_search_returns_results(self) -> None:
        """Search returns ranked results."""
        index = FAISSIndex()
        chunks, embeddings = self._make_chunks_and_embeddings(10)
        index.add(chunks, embeddings)

        query = np.random.randn(1, 384).astype(np.float32)
        results = index.search(query, top_k=3)

        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].rank == 0
        assert results[1].rank == 1

    def test_search_empty_index(self) -> None:
        """Search on empty index returns empty list."""
        index = FAISSIndex()
        query = np.random.randn(1, 384).astype(np.float32)
        results = index.search(query)
        assert results == []

    def test_search_top_k_exceeds_size(self) -> None:
        """Requesting more results than index size returns all available."""
        index = FAISSIndex()
        chunks, embeddings = self._make_chunks_and_embeddings(3)
        index.add(chunks, embeddings)

        query = np.random.randn(1, 384).astype(np.float32)
        results = index.search(query, top_k=10)
        assert len(results) == 3

    def test_save_and_load(self) -> None:
        """Index can be saved and loaded with data intact."""
        index = FAISSIndex()
        chunks, embeddings = self._make_chunks_and_embeddings(5)
        index.add(chunks, embeddings)

        with tempfile.TemporaryDirectory() as tmpdir:
            index.save(tmpdir)

            loaded = FAISSIndex.load(tmpdir)
            assert loaded.size == 5
            assert len(loaded.chunks) == 5
            assert loaded.chunks[0].content == "Chunk 0 about compliance rule 0"
            assert loaded.chunks[0].metadata["rule_id"] == "rule_0"

    def test_load_missing_directory_raises(self) -> None:
        """Loading from nonexistent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            FAISSIndex.load("/nonexistent/path")

    def test_search_with_real_embeddings(self) -> None:
        """End-to-end: embed text, index, search, get relevant result."""
        chunks = [
            DocumentChunk(
                content="GDPR requires explicit consent for data processing", chunk_index=0, source_file="gdpr.md"
            ),
            DocumentChunk(
                content="Bias in AI systems must be actively monitored", chunk_index=1, source_file="bias.md"
            ),
            DocumentChunk(content="PII like email addresses must be masked", chunk_index=2, source_file="pii.md"),
        ]
        texts = [c.content for c in chunks]
        embeddings = generate_embeddings(texts)

        index = FAISSIndex(dimension=embeddings.shape[1])
        index.add(chunks, embeddings)

        # Search for something related to GDPR
        query_emb = generate_embeddings(["data protection consent regulations"])
        results = index.search(query_emb, top_k=1)

        assert len(results) == 1
        assert "GDPR" in results[0].chunk.content or "consent" in results[0].chunk.content
