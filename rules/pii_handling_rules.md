# PII Handling Rules

## Rule 1: PII Detection Categories

The following data types must be detected and flagged:

- **Email addresses**: any@domain.tld patterns
- **Phone numbers**: international formats (+XX, country codes)
- **Credit card numbers**: 13-19 digit sequences matching Luhn algorithm
- **Social security numbers**: XXX-XX-XXXX patterns (US), country-specific formats
- **IP addresses**: IPv4 and IPv6 formats
- **Physical addresses**: street + city + postal code combinations
- **Dates of birth**: when associated with identifying information

## Rule 2: PII in Responses

AI must never generate responses containing real PII. When examples are needed,
use clearly fictional data (e.g., "Jane Doe", "jane.doe@example.com", "555-0100").

## Rule 3: PII in Prompts

When user prompts contain PII, the system must:

1. Log a warning (without storing the PII itself)
2. Process the request without echoing the PII back
3. Suggest to the user that they avoid sharing sensitive data

## Rule 4: PII Masking

When PII must be referenced, use masking: j***@example.com, +33 *** **\* **29
