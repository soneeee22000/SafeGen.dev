/**
 * TypeScript interfaces mirroring backend Pydantic models.
 * Uses snake_case to match JSON responses exactly.
 */

export interface ValidationFlag {
  layer: string;
  severity: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ComplianceResult {
  passed: boolean;
  score: number;
  flags: ValidationFlag[];
  layers_run: string[];
}

export interface ValidateRequest {
  prompt: string;
  context?: string;
  rules_category?: RulesCategory;
  stream?: boolean;
}

export interface ValidateResponse {
  response: string;
  raw_response?: string;
  compliance?: ComplianceResult;
  model: string;
  usage?: Record<string, unknown>;
}

export interface AuditRecord {
  request_id: string;
  timestamp: string;
  duration_ms: number;
  prompt: string;
  rules_category: string;
  response_content: string;
  model: string;
  usage?: Record<string, unknown>;
  compliance_passed: boolean;
  compliance_score: number;
  compliance_flags: Record<string, unknown>[];
  layers_run: string[];
}

export interface AuditListResponse {
  records: AuditRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface TimeSeriesPoint {
  date: string;
  total_requests: number;
  passed: number;
  failed: number;
  avg_score: number;
}

export interface FlagBreakdown {
  layer: string;
  severity: string;
  count: number;
}

export interface MetricsResponse {
  total_requests: number;
  total_passed: number;
  total_failed: number;
  compliance_rate: number;
  avg_score: number;
  avg_duration_ms: number;
  flags_breakdown: FlagBreakdown[];
  time_series: TimeSeriesPoint[];
  date_from: string;
  date_to: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface RuleDocument {
  filename: string;
  chunk_count: number;
}

export type RulesCategory = "safety" | "bias" | "pii" | "regulatory" | "all";

export type AuditStatus = "passed" | "failed" | "all";
