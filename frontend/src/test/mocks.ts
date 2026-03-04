/**
 * Factory functions for creating mock test data.
 */

import type {
  AuditListResponse,
  AuditRecord,
  FlagBreakdown,
  MetricsResponse,
  RuleDocument,
  TimeSeriesPoint,
} from "@/types";

export function createAuditRecord(
  overrides: Partial<AuditRecord> = {},
): AuditRecord {
  return {
    request_id: "req-abc-123",
    timestamp: "2025-01-15T10:30:00Z",
    duration_ms: 245,
    prompt: "Test prompt for compliance check",
    rules_category: "all",
    response_content: "This is a test response.",
    model: "gpt-4o",
    usage: { prompt_tokens: 50, completion_tokens: 100 },
    compliance_passed: true,
    compliance_score: 0.95,
    compliance_flags: [],
    layers_run: ["pii", "bias", "safety"],
    ...overrides,
  };
}

export function createTimeSeriesPoint(
  overrides: Partial<TimeSeriesPoint> = {},
): TimeSeriesPoint {
  return {
    date: "2025-01-15",
    total_requests: 10,
    passed: 8,
    failed: 2,
    avg_score: 0.85,
    ...overrides,
  };
}

export function createFlagBreakdown(
  overrides: Partial<FlagBreakdown> = {},
): FlagBreakdown {
  return {
    layer: "pii",
    severity: "critical",
    count: 5,
    ...overrides,
  };
}

export function createMetricsResponse(
  overrides: Partial<MetricsResponse> = {},
): MetricsResponse {
  return {
    total_requests: 100,
    total_passed: 85,
    total_failed: 15,
    compliance_rate: 0.85,
    avg_score: 0.88,
    avg_duration_ms: 320,
    flags_breakdown: [
      createFlagBreakdown({ layer: "pii", severity: "critical", count: 5 }),
      createFlagBreakdown({ layer: "bias", severity: "warning", count: 12 }),
    ],
    time_series: [
      createTimeSeriesPoint({
        date: "2025-01-14",
        total_requests: 8,
        passed: 7,
        failed: 1,
      }),
      createTimeSeriesPoint({
        date: "2025-01-15",
        total_requests: 10,
        passed: 8,
        failed: 2,
      }),
    ],
    date_from: "2025-01-01",
    date_to: "2025-01-15",
    ...overrides,
  };
}

export function createAuditListResponse(
  overrides: Partial<AuditListResponse> = {},
): AuditListResponse {
  return {
    records: [
      createAuditRecord(),
      createAuditRecord({
        request_id: "req-def-456",
        compliance_passed: false,
        compliance_score: 0.4,
      }),
    ],
    total: 2,
    limit: 20,
    offset: 0,
    ...overrides,
  };
}

export function createRuleDocument(
  overrides: Partial<RuleDocument> = {},
): RuleDocument {
  return {
    filename: "gdpr_content_rules.md",
    chunk_count: 5,
    ...overrides,
  };
}
