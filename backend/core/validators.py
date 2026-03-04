"""Compliance validators for SafeGen — PII detection, bias checking, safety filtering.

Each validator implements a `validate(text) -> list[ValidationFlag]` interface.
Validators are stateless and can be reused across requests.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from core.models import ValidationFlag

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Abstract base class for all compliance validators."""

    @abstractmethod
    def validate(self, text: str) -> list[ValidationFlag]:
        """Validate text and return a list of compliance flags.

        Args:
            text: The text to validate.

        Returns:
            List of ValidationFlag objects for any violations found.
            Empty list if text is clean.
        """


# ── PII Detector ─────────────────────────────────────────────────────────────

# Domains that are considered safe/fictional (not real PII)
_SAFE_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "test.com"}

# PII regex patterns: (pattern, pii_type, description)
_PII_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Email addresses (exclude safe domains)
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "email",
        "Email address detected",
    ),
    # US phone numbers: (555) 123-4567, 555-123-4567, 555.123.4567
    (
        re.compile(r"\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
        "phone",
        "US phone number detected",
    ),
    # International phone numbers: +XX XXXXXXXXX
    (
        re.compile(r"\+\d{1,3}[\s.-]?\d[\s.\d-]{6,14}\d"),
        "phone",
        "International phone number detected",
    ),
    # US Social Security Numbers: XXX-XX-XXXX
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "ssn",
        "Social Security Number detected",
    ),
    # Credit card numbers (13-19 digits, with optional spaces/dashes)
    (
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,7}\b"),
        "credit_card",
        "Credit card number detected",
    ),
    # IPv4 addresses (but not version numbers like 3.10.0)
    (
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\b"
        ),
        "ip_address",
        "IP address detected",
    ),
]

# SSN pattern — used to exclude false positives from date-like patterns
_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class PIIDetector(BaseValidator):
    """Detects personally identifiable information in text using regex patterns.

    Detects: email addresses, phone numbers, SSNs, credit card numbers, IP addresses.
    Example/fictional emails (e.g., @example.com) are excluded.
    """

    def validate(self, text: str) -> list[ValidationFlag]:
        """Scan text for PII patterns.

        Args:
            text: Text to scan.

        Returns:
            List of ValidationFlag with severity 'critical' for each PII found.
        """
        if not text.strip():
            return []

        flags: list[ValidationFlag] = []
        # Collect date-like patterns to exclude from SSN matches
        date_matches = {m.group() for m in _DATE_PATTERN.finditer(text)}

        for pattern, pii_type, description in _PII_PATTERNS:
            for match in pattern.finditer(text):
                matched_text = match.group()

                # Skip fictional/example emails
                if pii_type == "email":
                    domain = matched_text.split("@")[1].lower()
                    if domain in _SAFE_EMAIL_DOMAINS:
                        continue

                # Skip date-like patterns for SSN
                if pii_type == "ssn" and matched_text in date_matches:
                    continue

                # Skip version-like patterns for IP (e.g., "3.10.0")
                if pii_type == "ip_address":
                    octets = matched_text.split(".")
                    if any(int(o) > 255 for o in octets):
                        continue

                flags.append(
                    ValidationFlag(
                        layer="pii",
                        severity="critical",
                        message=f"{description}: {_mask_pii(matched_text)}",
                        details={
                            "pii_type": pii_type,
                            "position": match.start(),
                        },
                    )
                )

        logger.debug("PIIDetector found %d flags", len(flags))
        return flags


def _mask_pii(value: str) -> str:
    """Mask a PII value for safe logging.

    Args:
        value: The raw PII string.

    Returns:
        Masked version showing only first and last 2 chars.
    """
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


# ── Bias Checker ─────────────────────────────────────────────────────────────

# Gendered job titles → neutral alternatives
_GENDERED_TERMS: dict[str, str] = {
    "chairman": "chairperson",
    "chairwoman": "chairperson",
    "fireman": "firefighter",
    "firewoman": "firefighter",
    "policeman": "police officer",
    "policewoman": "police officer",
    "stewardess": "flight attendant",
    "steward": "flight attendant",
    "mailman": "mail carrier",
    "mankind": "humankind",
    "manpower": "workforce",
    "man-made": "synthetic",
    "workman": "worker",
    "businessman": "business professional",
    "businesswoman": "business professional",
    "salesman": "salesperson",
    "saleswoman": "salesperson",
    "spokesman": "spokesperson",
    "spokeswoman": "spokesperson",
    "waitress": "server",
    "waiter": "server",
}

# Ableist terms to flag
_ABLEIST_TERMS: list[str] = [
    "crazy",
    "insane",
    "lame",
    "dumb",
    "retarded",
    "crippled",
    "handicapped",
    "psycho",
    "moron",
    "idiot",
]

# Stereotypical phrases (regex patterns)
_STEREOTYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"\bwomen\s+are\s+(?:naturally|inherently|always)\b", re.IGNORECASE),
        "Gender stereotype about women",
    ),
    (
        re.compile(r"\bmen\s+are\s+(?:naturally|inherently|always)\b", re.IGNORECASE),
        "Gender stereotype about men",
    ),
    (
        re.compile(r"\bold\s+people\s+(?:can'?t|cannot|don'?t|are\s+unable)\b", re.IGNORECASE),
        "Age-based stereotype",
    ),
    (
        re.compile(r"\byoung\s+people\s+(?:can'?t|cannot|don'?t|are\s+unable)\b", re.IGNORECASE),
        "Age-based stereotype",
    ),
    (
        re.compile(r"\b(?:all|every)\s+(?:men|women|blacks|whites|asians)\b", re.IGNORECASE),
        "Racial/gender generalization",
    ),
]


class BiasChecker(BaseValidator):
    """Detects biased, stereotypical, or non-inclusive language.

    Checks for: gendered job titles, ableist language, stereotypical phrases,
    age-based assumptions.
    """

    def validate(self, text: str) -> list[ValidationFlag]:
        """Scan text for biased language.

        Args:
            text: Text to scan.

        Returns:
            List of ValidationFlag with severity 'warning' for each bias found.
        """
        if not text.strip():
            return []

        flags: list[ValidationFlag] = []
        text_lower = text.lower()

        # Check gendered terms
        for term, alternative in _GENDERED_TERMS.items():
            if re.search(rf"\b{re.escape(term)}\b", text_lower):
                flags.append(
                    ValidationFlag(
                        layer="bias",
                        severity="warning",
                        message=f"Gendered term '{term}' detected; consider '{alternative}'",
                        details={
                            "bias_type": "gender",
                            "term": term,
                            "suggestion": alternative,
                        },
                    )
                )

        # Check ableist terms
        for term in _ABLEIST_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", text_lower):
                flags.append(
                    ValidationFlag(
                        layer="bias",
                        severity="warning",
                        message=f"Potentially ableist term '{term}' detected",
                        details={
                            "bias_type": "ableist",
                            "term": term,
                        },
                    )
                )

        # Check stereotypical patterns
        for pattern, description in _STEREOTYPE_PATTERNS:
            if pattern.search(text):
                flags.append(
                    ValidationFlag(
                        layer="bias",
                        severity="warning",
                        message=description,
                        details={
                            "bias_type": "stereotype",
                            "pattern": description,
                        },
                    )
                )

        logger.debug("BiasChecker found %d flags", len(flags))
        return flags


# ── Safety Filter ────────────────────────────────────────────────────────────

# Safety category patterns: (compiled_regex, category, description)
# These detect clearly harmful instructional or inciting content.
# Educational/medical/clinical language is excluded via context patterns.
_SAFETY_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Hate speech / elimination rhetoric
    (
        re.compile(
            r"\b(?:should\s+be\s+(?:eliminated|exterminated|killed|destroyed|eradicated)|"
            r"death\s+to\s+(?:all|every)|"
            r"get\s+rid\s+of\s+(?:all|every)\s+\w+\s+people)\b",
            re.IGNORECASE,
        ),
        "hate",
        "Hate speech or eliminationist rhetoric detected",
    ),
    # Violence instructions
    (
        re.compile(
            r"\b(?:how\s+to\s+(?:build\s+a\s+(?:weapon|bomb|explosive)|"
            r"make\s+(?:a\s+weapon|poison|explosive)|"
            r"hurt|kill|attack|assault)\b|"
            r"instructions?\s+to\s+(?:harm|hurt|kill|attack|build\s+a\s+weapon))\b",
            re.IGNORECASE,
        ),
        "violence",
        "Violent or harmful instructional content detected",
    ),
    # Self-harm
    (
        re.compile(
            r"\b(?:(?:how\s+to|methods?\s+to|ways?\s+to)\s+"
            r"(?:harm\s+yourself|end\s+(?:your|my)\s+life|commit\s+suicide|self.?harm)|"
            r"(?:cut|hurt|injure)\s+yourself)\b",
            re.IGNORECASE,
        ),
        "self_harm",
        "Self-harm related content detected",
    ),
]

# Educational/clinical context — if present, don't flag self-harm/violence
_EDUCATIONAL_CONTEXT = re.compile(
    r"\b(?:medical\s+professional|healthcare|clinical|therapist|counselor|"
    r"mental\s+health\s+referral|risk\s+assessment|prevention|"
    r"if\s+you\s+or\s+someone|national\s+suicide|crisis\s+hotline)\b",
    re.IGNORECASE,
)


class SafetyFilter(BaseValidator):
    """Detects harmful content: hate speech, violence, self-harm.

    Uses pattern matching with educational context exclusion to avoid
    over-flagging clinical or preventive content.
    """

    def validate(self, text: str) -> list[ValidationFlag]:
        """Scan text for harmful content.

        Args:
            text: Text to scan.

        Returns:
            List of ValidationFlag with severity 'critical' for harmful content.
        """
        if not text.strip():
            return []

        flags: list[ValidationFlag] = []
        is_educational = bool(_EDUCATIONAL_CONTEXT.search(text))

        for pattern, category, description in _SAFETY_PATTERNS:
            if pattern.search(text):
                # Skip flagging if the content appears educational/clinical
                if is_educational and category in ("self_harm", "violence"):
                    logger.debug("Skipping %s flag due to educational context", category)
                    continue

                flags.append(
                    ValidationFlag(
                        layer="safety",
                        severity="critical",
                        message=description,
                        details={
                            "safety_category": category,
                        },
                    )
                )

        logger.debug("SafetyFilter found %d flags", len(flags))
        return flags
