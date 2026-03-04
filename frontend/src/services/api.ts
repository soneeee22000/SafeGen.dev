/**
 * Typed API client for SafeGen backend endpoints.
 */

import type {
  AuditListResponse,
  AuditStatus,
  MetricsResponse,
  RuleDocument,
  ValidateRequest,
  ValidateResponse,
} from "@/types";

/** Custom error class with status code and optional details. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Base fetch wrapper with error handling.
 */
async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    let details: Record<string, unknown> | undefined;
    try {
      details = await response.json();
    } catch {
      /* empty */
    }
    throw new ApiError(
      response.status,
      (details?.message as string) ?? response.statusText,
      details,
    );
  }
  return response.json() as Promise<T>;
}

/** Fetch aggregated metrics. */
export function fetchMetrics(
  dateFrom?: string,
  dateTo?: string,
): Promise<MetricsResponse> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const qs = params.toString();
  return apiFetch<MetricsResponse>(`/api/metrics${qs ? `?${qs}` : ""}`);
}

/** Fetch paginated audit records. */
export function fetchAuditRecords(options: {
  dateFrom?: string;
  dateTo?: string;
  status?: AuditStatus;
  limit?: number;
  offset?: number;
}): Promise<AuditListResponse> {
  const params = new URLSearchParams();
  if (options.dateFrom) params.set("date_from", options.dateFrom);
  if (options.dateTo) params.set("date_to", options.dateTo);
  if (options.status && options.status !== "all")
    params.set("status", options.status);
  if (options.limit) params.set("limit", options.limit.toString());
  if (options.offset) params.set("offset", options.offset.toString());
  const qs = params.toString();
  return apiFetch<AuditListResponse>(`/api/audit${qs ? `?${qs}` : ""}`);
}

/** Fetch list of ingested rules. */
export function fetchRules(): Promise<RuleDocument[]> {
  return apiFetch<RuleDocument[]>("/api/rules");
}

/** Upload a rule document for ingestion. */
export async function ingestRuleFile(file: File): Promise<{ message: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<{ message: string }>("/api/rules/ingest", {
    method: "POST",
    body: formData,
  });
}

/** Send a prompt for validation. */
export function validatePrompt(
  request: ValidateRequest,
): Promise<ValidateResponse> {
  return apiFetch<ValidateResponse>("/api/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}
