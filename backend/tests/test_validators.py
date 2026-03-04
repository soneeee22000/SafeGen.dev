"""Tests for core.validators — PII detection, bias checking, safety filtering."""

from __future__ import annotations

import pytest

from core.models import ValidationFlag
from core.validators import BiasChecker, PIIDetector, SafetyFilter

# ── PIIDetector Tests ────────────────────────────────────────────────────────


class TestPIIDetector:
    """Tests for PII detection across multiple categories."""

    def setup_method(self) -> None:
        """Create a fresh detector for each test."""
        self.detector = PIIDetector()

    # ── Email detection ──

    def test_detects_email_address(self) -> None:
        """Flag text containing an email address."""
        flags = self.detector.validate("Contact us at john.doe@company.com for help.")
        assert len(flags) >= 1
        email_flags = [f for f in flags if "email" in f.details.get("pii_type", "")]
        assert len(email_flags) == 1
        assert email_flags[0].severity == "critical"
        assert email_flags[0].layer == "pii"

    def test_ignores_example_emails(self) -> None:
        """Do NOT flag example.com emails (they're fictional)."""
        flags = self.detector.validate("Use jane.doe@example.com as a placeholder.")
        email_flags = [f for f in flags if "email" in f.details.get("pii_type", "")]
        assert len(email_flags) == 0

    # ── Phone number detection ──

    def test_detects_us_phone_number(self) -> None:
        """Flag US phone numbers."""
        flags = self.detector.validate("Call me at (555) 123-4567 or 555-123-4567.")
        phone_flags = [f for f in flags if "phone" in f.details.get("pii_type", "")]
        assert len(phone_flags) >= 1

    def test_detects_international_phone_number(self) -> None:
        """Flag international phone numbers with country code."""
        flags = self.detector.validate("Reach us at +33 6 12 34 56 78.")
        phone_flags = [f for f in flags if "phone" in f.details.get("pii_type", "")]
        assert len(phone_flags) >= 1

    # ── SSN detection ──

    def test_detects_ssn(self) -> None:
        """Flag US Social Security Numbers."""
        flags = self.detector.validate("My SSN is 123-45-6789.")
        ssn_flags = [f for f in flags if "ssn" in f.details.get("pii_type", "")]
        assert len(ssn_flags) == 1
        assert ssn_flags[0].severity == "critical"

    def test_ignores_non_ssn_dashes(self) -> None:
        """Do NOT flag date-like patterns as SSN."""
        flags = self.detector.validate("The reference is 2024-01-15.")
        ssn_flags = [f for f in flags if "ssn" in f.details.get("pii_type", "")]
        assert len(ssn_flags) == 0

    # ── Credit card detection ──

    def test_detects_credit_card_visa(self) -> None:
        """Flag Visa credit card numbers."""
        flags = self.detector.validate("Card: 4111 1111 1111 1111")
        cc_flags = [f for f in flags if "credit_card" in f.details.get("pii_type", "")]
        assert len(cc_flags) == 1
        assert cc_flags[0].severity == "critical"

    def test_detects_credit_card_no_spaces(self) -> None:
        """Flag credit card numbers without spaces."""
        flags = self.detector.validate("Card: 4111111111111111")
        cc_flags = [f for f in flags if "credit_card" in f.details.get("pii_type", "")]
        assert len(cc_flags) == 1

    # ── IP address detection ──

    def test_detects_ipv4_address(self) -> None:
        """Flag IPv4 addresses."""
        flags = self.detector.validate("Server IP is 192.168.1.100.")
        ip_flags = [f for f in flags if "ip_address" in f.details.get("pii_type", "")]
        assert len(ip_flags) == 1

    def test_ignores_version_numbers(self) -> None:
        """Do NOT flag version numbers as IP addresses."""
        flags = self.detector.validate("Use Python version 3.10.0.")
        ip_flags = [f for f in flags if "ip_address" in f.details.get("pii_type", "")]
        assert len(ip_flags) == 0

    # ── Clean text ──

    def test_clean_text_returns_no_flags(self) -> None:
        """No PII in clean text produces zero flags."""
        flags = self.detector.validate("This is a general compliance guideline.")
        assert flags == []

    def test_multiple_pii_types_in_one_text(self) -> None:
        """Detect multiple PII types in the same text."""
        text = "Email: real@company.com, SSN: 123-45-6789, Phone: (555) 123-4567"
        flags = self.detector.validate(text)
        pii_types = {f.details.get("pii_type") for f in flags}
        assert "email" in pii_types
        assert "ssn" in pii_types
        assert "phone" in pii_types

    def test_empty_text_returns_no_flags(self) -> None:
        """Empty string produces zero flags."""
        flags = self.detector.validate("")
        assert flags == []


# ── BiasChecker Tests ────────────────────────────────────────────────────────


class TestBiasChecker:
    """Tests for bias detection in LLM outputs."""

    def setup_method(self) -> None:
        """Create a fresh checker for each test."""
        self.checker = BiasChecker()

    def test_detects_gendered_job_titles(self) -> None:
        """Flag gendered job titles like 'chairman', 'fireman'."""
        flags = self.checker.validate("The chairman announced the new policy.")
        assert len(flags) >= 1
        assert flags[0].layer == "bias"
        assert flags[0].severity == "warning"
        assert "gender" in flags[0].details.get("bias_type", "").lower()

    def test_detects_stereotypical_language(self) -> None:
        """Flag stereotypical associations."""
        flags = self.checker.validate("Women are naturally better at nurturing.")
        assert len(flags) >= 1

    def test_detects_ableist_language(self) -> None:
        """Flag ableist terms."""
        flags = self.checker.validate("That idea is crazy and lame.")
        assert len(flags) >= 1
        ableist_flags = [f for f in flags if "ableist" in f.details.get("bias_type", "").lower()]
        assert len(ableist_flags) >= 1

    def test_detects_age_bias(self) -> None:
        """Flag age-related stereotyping."""
        flags = self.checker.validate("Old people can't understand technology.")
        assert len(flags) >= 1

    def test_neutral_text_returns_no_flags(self) -> None:
        """Neutral, inclusive text returns zero flags."""
        flags = self.checker.validate(
            "The team lead presented the quarterly results to stakeholders."
        )
        assert flags == []

    def test_severity_is_warning_not_critical(self) -> None:
        """Bias flags should be 'warning' severity, not 'critical'."""
        flags = self.checker.validate("The fireman saved the child.")
        for flag in flags:
            assert flag.severity == "warning"

    def test_empty_text_returns_no_flags(self) -> None:
        """Empty string produces zero flags."""
        flags = self.checker.validate("")
        assert flags == []


# ── SafetyFilter Tests ───────────────────────────────────────────────────────


class TestSafetyFilter:
    """Tests for harmful content detection."""

    def setup_method(self) -> None:
        """Create a fresh filter for each test."""
        self.filter = SafetyFilter()

    def test_detects_hate_speech(self) -> None:
        """Flag hate speech / discriminatory content."""
        flags = self.filter.validate("All members of that group should be eliminated.")
        assert len(flags) >= 1
        assert flags[0].layer == "safety"
        assert flags[0].severity == "critical"
        assert "hate" in flags[0].details.get("safety_category", "").lower()

    def test_detects_violence_content(self) -> None:
        """Flag violent content."""
        flags = self.filter.validate("Here is how to build a weapon to hurt people.")
        assert len(flags) >= 1
        violence_flags = [f for f in flags if "violence" in f.details.get("safety_category", "").lower()]
        assert len(violence_flags) >= 1

    def test_detects_self_harm_content(self) -> None:
        """Flag self-harm related content."""
        flags = self.filter.validate("Here are methods to harm yourself.")
        assert len(flags) >= 1
        harm_flags = [f for f in flags if "self_harm" in f.details.get("safety_category", "").lower()]
        assert len(harm_flags) >= 1

    def test_safe_text_returns_no_flags(self) -> None:
        """Safe, helpful text returns zero flags."""
        flags = self.filter.validate(
            "Regular exercise and a balanced diet contribute to overall health."
        )
        assert flags == []

    def test_safety_flags_are_critical(self) -> None:
        """Safety violations should be 'critical' severity."""
        flags = self.filter.validate("Instructions to harm someone violently.")
        for flag in flags:
            assert flag.severity == "critical"

    def test_empty_text_returns_no_flags(self) -> None:
        """Empty string produces zero flags."""
        flags = self.filter.validate("")
        assert flags == []

    def test_educational_context_not_flagged(self) -> None:
        """Educational/medical content should not be over-flagged."""
        flags = self.filter.validate(
            "Medical professionals should assess patient risk factors for self-harm "
            "and provide appropriate mental health referrals."
        )
        assert flags == []


# ── Validator Interface Tests ────────────────────────────────────────────────


class TestValidatorInterface:
    """Tests for shared validator behavior."""

    @pytest.mark.parametrize("validator_cls", [PIIDetector, BiasChecker, SafetyFilter])
    def test_validate_returns_list_of_validation_flags(self, validator_cls: type) -> None:
        """All validators return list[ValidationFlag]."""
        validator = validator_cls()
        result = validator.validate("Some test text.")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, ValidationFlag)

    @pytest.mark.parametrize("validator_cls", [PIIDetector, BiasChecker, SafetyFilter])
    def test_validate_on_empty_string(self, validator_cls: type) -> None:
        """All validators handle empty string gracefully."""
        validator = validator_cls()
        result = validator.validate("")
        assert result == []
