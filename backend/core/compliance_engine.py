"""Compliance engine — orchestrates all validation layers for SafeGen.

Runs PII detection, bias checking, safety filtering, and optionally
RAG-based rule compliance evaluation. Aggregates results into a
ComplianceResult with a score and pass/fail determination.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.models import ComplianceResult, RulesCategory, ValidationFlag
from core.rag_pipeline import FAISSIndex, generate_embeddings
from core.validators import BaseValidator, BiasChecker, PIIDetector, SafetyFilter

logger = logging.getLogger(__name__)

# Score penalties per severity level
_SEVERITY_PENALTIES: dict[str, float] = {
    "critical": 0.3,
    "warning": 0.1,
    "info": 0.0,
}

# Which validators to run for each category
_CATEGORY_LAYERS: dict[RulesCategory, list[str]] = {
    RulesCategory.PII: ["pii"],
    RulesCategory.BIAS: ["bias"],
    RulesCategory.SAFETY: ["safety"],
    RulesCategory.REGULATORY: ["pii", "bias", "safety"],
    RulesCategory.ALL: ["pii", "bias", "safety"],
}


class ComplianceEngine:
    """Orchestrates compliance validation across multiple layers.

    Runs configurable validators against LLM output and produces
    an aggregate ComplianceResult with score and flags.

    Args:
        faiss_index: Optional FAISS index for RAG-based rule compliance.
            When provided, a 'compliance' layer is added that retrieves
            relevant rule chunks and checks text against them.
    """

    def __init__(self, faiss_index: Optional[FAISSIndex] = None) -> None:
        """Initialize the compliance engine with default validators.

        Args:
            faiss_index: Optional FAISS index for rule-based compliance checking.
        """
        self.validators: list[tuple[str, BaseValidator]] = [
            ("pii", PIIDetector()),
            ("bias", BiasChecker()),
            ("safety", SafetyFilter()),
        ]
        self.faiss_index = faiss_index

    def validate(
        self,
        text: str,
        rules_category: RulesCategory = RulesCategory.ALL,
    ) -> ComplianceResult:
        """Run all applicable validation layers on the given text.

        Args:
            text: The LLM response text to validate.
            rules_category: Which category of rules to validate against.
                Controls which validators run.

        Returns:
            ComplianceResult with pass/fail, score, flags, and layers_run.
        """
        all_flags: list[ValidationFlag] = []
        layers_run: list[str] = []

        # Determine which layers to run based on category
        active_layers = _CATEGORY_LAYERS.get(rules_category, _CATEGORY_LAYERS[RulesCategory.ALL])

        # Run each active validator
        for layer_name, validator in self.validators:
            if layer_name not in active_layers:
                continue

            logger.info("Running %s validator", layer_name)
            flags = validator.validate(text)
            all_flags.extend(flags)
            layers_run.append(layer_name)

        # Run RAG-based rule compliance if FAISS index is available
        if self.faiss_index is not None and self.faiss_index.size > 0:
            compliance_flags = self._run_rule_compliance(text)
            all_flags.extend(compliance_flags)
            layers_run.append("compliance")

        # Calculate score and pass/fail
        score = self._calculate_score(all_flags)
        passed = self._determine_pass(all_flags)

        result = ComplianceResult(
            passed=passed,
            score=score,
            flags=all_flags,
            layers_run=layers_run,
        )

        logger.info(
            "Compliance check complete: passed=%s, score=%.2f, flags=%d, layers=%s",
            passed,
            score,
            len(all_flags),
            layers_run,
        )
        return result

    def _run_rule_compliance(self, text: str) -> list[ValidationFlag]:
        """Run RAG-based rule compliance checking.

        Retrieves the most relevant rule chunks from the FAISS index
        and returns informational flags about which rules were matched.

        Args:
            text: The text to check against indexed rules.

        Returns:
            List of ValidationFlag with matched rule information.
        """
        if self.faiss_index is None or self.faiss_index.size == 0:
            return []

        try:
            query_embedding = generate_embeddings([text])
            results = self.faiss_index.search(query_embedding, top_k=3)
        except Exception:
            logger.exception("RAG rule compliance check failed")
            return []

        flags: list[ValidationFlag] = []
        for result in results:
            if result.score > 0.5:
                flags.append(
                    ValidationFlag(
                        layer="compliance",
                        severity="info",
                        message=f"Relevant rule from '{result.chunk.source_file}': {result.chunk.content[:100]}",
                        details={
                            "source_file": result.chunk.source_file,
                            "chunk_index": result.chunk.chunk_index,
                            "similarity_score": round(float(result.score), 4),
                            "rule_id": result.chunk.metadata.get("rule_id", ""),
                        },
                    )
                )

        return flags

    @staticmethod
    def _calculate_score(flags: list[ValidationFlag]) -> float:
        """Calculate compliance score from 0.0 to 1.0.

        Starts at 1.0 and deducts based on flag severity.
        Critical flags deduct 0.3, warnings deduct 0.1.

        Args:
            flags: List of validation flags.

        Returns:
            Score clamped between 0.0 and 1.0.
        """
        if not flags:
            return 1.0

        total_penalty = sum(_SEVERITY_PENALTIES.get(f.severity, 0.0) for f in flags)
        score = max(0.0, 1.0 - total_penalty)
        return round(score, 4)

    @staticmethod
    def _determine_pass(flags: list[ValidationFlag]) -> bool:
        """Determine pass/fail based on flag severities.

        Any 'critical' severity flag causes a failure.
        Warnings alone do not cause failure.

        Args:
            flags: List of validation flags.

        Returns:
            True if no critical flags, False otherwise.
        """
        return not any(f.severity == "critical" for f in flags)
