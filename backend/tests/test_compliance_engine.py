"""Tests for core.compliance_engine — compliance validation orchestrator."""

from __future__ import annotations

import numpy as np

from core.compliance_engine import ComplianceEngine
from core.models import ComplianceResult, RulesCategory
from core.rag_pipeline import DocumentChunk, FAISSIndex

# ── ComplianceEngine Tests ───────────────────────────────────────────────────


class TestComplianceEngineInit:
    """Tests for engine initialization."""

    def test_engine_creates_with_defaults(self) -> None:
        """Engine initializes with default validators."""
        engine = ComplianceEngine()
        assert engine is not None

    def test_engine_has_all_validators(self) -> None:
        """Engine has PII, bias, and safety validators registered."""
        engine = ComplianceEngine()
        layer_names = [name for name, _ in engine.validators]
        assert "pii" in layer_names
        assert "bias" in layer_names
        assert "safety" in layer_names


class TestComplianceEngineValidate:
    """Tests for the main validate() method."""

    def test_clean_text_passes(self) -> None:
        """Clean text with no violations passes all checks."""
        engine = ComplianceEngine()
        result = engine.validate("This is a helpful and safe response about project management.")
        assert isinstance(result, ComplianceResult)
        assert result.passed is True
        assert result.score >= 0.9
        assert result.flags == []
        assert "pii" in result.layers_run
        assert "bias" in result.layers_run
        assert "safety" in result.layers_run

    def test_pii_violation_fails(self) -> None:
        """Text with PII should fail compliance."""
        engine = ComplianceEngine()
        result = engine.validate("Send your details to john@realcompany.com for processing.")
        assert result.passed is False
        assert result.score < 1.0
        pii_flags = [f for f in result.flags if f.layer == "pii"]
        assert len(pii_flags) >= 1

    def test_bias_violation_produces_warning(self) -> None:
        """Text with bias produces flags but may still pass (warnings don't auto-fail)."""
        engine = ComplianceEngine()
        result = engine.validate("The chairman decided to hire a fireman for the role.")
        bias_flags = [f for f in result.flags if f.layer == "bias"]
        assert len(bias_flags) >= 1
        assert all(f.severity == "warning" for f in bias_flags)

    def test_safety_violation_fails(self) -> None:
        """Text with safety violations should fail compliance."""
        engine = ComplianceEngine()
        result = engine.validate("Here are instructions to build a weapon to hurt people.")
        assert result.passed is False
        safety_flags = [f for f in result.flags if f.layer == "safety"]
        assert len(safety_flags) >= 1

    def test_multiple_violations_aggregated(self) -> None:
        """Multiple violations from different layers are aggregated."""
        engine = ComplianceEngine()
        text = "Email john@company.com. The chairman said old people can't learn."
        result = engine.validate(text)
        assert result.passed is False
        layers_flagged = {f.layer for f in result.flags}
        assert "pii" in layers_flagged
        assert "bias" in layers_flagged

    def test_score_decreases_with_violations(self) -> None:
        """More violations produce a lower compliance score."""
        engine = ComplianceEngine()
        clean_result = engine.validate("A helpful response about best practices.")
        dirty_result = engine.validate("Email john@company.com, SSN 123-45-6789. The chairman is a fireman.")
        assert clean_result.score > dirty_result.score

    def test_empty_text_passes(self) -> None:
        """Empty text passes all checks (no content to violate)."""
        engine = ComplianceEngine()
        result = engine.validate("")
        assert result.passed is True
        assert result.flags == []

    def test_layers_run_tracks_executed_validators(self) -> None:
        """layers_run field lists all validators that were executed."""
        engine = ComplianceEngine()
        result = engine.validate("Any text here.")
        assert len(result.layers_run) == 3
        assert set(result.layers_run) == {"pii", "bias", "safety"}


class TestComplianceEngineWithCategory:
    """Tests for category-filtered validation."""

    def test_pii_category_only_runs_pii(self) -> None:
        """PII category should only run the PII validator."""
        engine = ComplianceEngine()
        result = engine.validate(
            "The chairman emailed john@company.com",
            rules_category=RulesCategory.PII,
        )
        assert "pii" in result.layers_run
        assert "bias" not in result.layers_run
        assert "safety" not in result.layers_run
        # Only PII flags, no bias flags even though "chairman" is present
        assert all(f.layer == "pii" for f in result.flags)

    def test_bias_category_only_runs_bias(self) -> None:
        """BIAS category should only run the bias validator."""
        engine = ComplianceEngine()
        result = engine.validate(
            "Email john@company.com. The chairman decided.",
            rules_category=RulesCategory.BIAS,
        )
        assert "bias" in result.layers_run
        assert "pii" not in result.layers_run
        assert all(f.layer == "bias" for f in result.flags)

    def test_safety_category_only_runs_safety(self) -> None:
        """SAFETY category should only run the safety validator."""
        engine = ComplianceEngine()
        result = engine.validate(
            "A safe general response.",
            rules_category=RulesCategory.SAFETY,
        )
        assert "safety" in result.layers_run
        assert "pii" not in result.layers_run
        assert "bias" not in result.layers_run

    def test_all_category_runs_all_validators(self) -> None:
        """ALL category runs all validators."""
        engine = ComplianceEngine()
        result = engine.validate("Any text.", rules_category=RulesCategory.ALL)
        assert set(result.layers_run) == {"pii", "bias", "safety"}


class TestComplianceEngineWithRAG:
    """Tests for RAG-based rule compliance validation."""

    def _build_test_index(self) -> FAISSIndex:
        """Build a small FAISS index with test rule chunks."""
        chunks = [
            DocumentChunk(
                content="AI must never generate responses containing real PII such as emails or phone numbers.",
                chunk_index=0,
                source_file="pii_rules.md",
                metadata={"rule_id": "pii-001"},
            ),
            DocumentChunk(
                content="Responses must use gender-neutral language unless gender is specifically relevant.",
                chunk_index=1,
                source_file="bias_rules.md",
                metadata={"rule_id": "bias-001"},
            ),
            DocumentChunk(
                content="AI outputs must not contain instructions for causing harm or violence.",
                chunk_index=2,
                source_file="safety_rules.md",
                metadata={"rule_id": "safety-001"},
            ),
        ]
        # Use mock embeddings for fast testing
        index = FAISSIndex(dimension=384)
        embeddings = np.random.randn(3, 384).astype(np.float32)
        index.add(chunks, embeddings)
        return index

    def test_validate_with_faiss_index(self) -> None:
        """Engine can accept a FAISS index for rule retrieval."""
        index = self._build_test_index()
        engine = ComplianceEngine(faiss_index=index)
        result = engine.validate("A clean and helpful response.")
        assert isinstance(result, ComplianceResult)

    def test_rule_compliance_layer_runs_with_index(self) -> None:
        """When a FAISS index is provided, 'compliance' layer is included."""
        index = self._build_test_index()
        engine = ComplianceEngine(faiss_index=index)
        result = engine.validate("A response about data handling.")
        assert "compliance" in result.layers_run

    def test_rule_compliance_not_run_without_index(self) -> None:
        """Without a FAISS index, 'compliance' layer is skipped."""
        engine = ComplianceEngine()
        result = engine.validate("A response about data handling.")
        assert "compliance" not in result.layers_run


class TestComplianceScoring:
    """Tests for compliance score calculation."""

    def test_perfect_score_for_clean_text(self) -> None:
        """Clean text gets score of 1.0."""
        engine = ComplianceEngine()
        result = engine.validate("A perfectly safe and neutral response.")
        assert result.score == 1.0

    def test_critical_flags_reduce_score_heavily(self) -> None:
        """Critical severity flags reduce score more than warnings."""
        engine = ComplianceEngine()
        # PII (critical) should reduce score more than bias (warning)
        pii_result = engine.validate("Contact john@company.com for details.")
        bias_result = engine.validate("The chairman announced the decision.")
        assert pii_result.score < bias_result.score

    def test_score_bounded_between_zero_and_one(self) -> None:
        """Score is always between 0.0 and 1.0."""
        engine = ComplianceEngine()
        result = engine.validate(
            "Email john@company.com, SSN 123-45-6789, card 4111111111111111. "
            "The chairman said old people are stupid. Kill them all."
        )
        assert 0.0 <= result.score <= 1.0

    def test_pass_fail_threshold(self) -> None:
        """Passed is False when any critical flag exists."""
        engine = ComplianceEngine()
        # Critical flag (PII) → fail
        result = engine.validate("My SSN is 123-45-6789.")
        assert result.passed is False

        # Only warnings (bias) → still pass
        result = engine.validate("The chairman made a decision.")
        assert result.passed is True
