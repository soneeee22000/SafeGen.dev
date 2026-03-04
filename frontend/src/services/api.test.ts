import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, fetchMetrics, fetchAuditRecords, fetchRules } from "./api";
import { createMetricsResponse, createAuditListResponse } from "@/test/mocks";

describe("API client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchMetrics", () => {
    it("fetches metrics without params", async () => {
      const mockData = createMetricsResponse();
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      } as Response);

      const result = await fetchMetrics();
      expect(result).toEqual(mockData);
      expect(fetch).toHaveBeenCalledWith("/api/metrics", undefined);
    });

    it("appends date params when provided", async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(createMetricsResponse()),
      } as Response);

      await fetchMetrics("2025-01-01", "2025-01-15");
      expect(fetch).toHaveBeenCalledWith(
        "/api/metrics?date_from=2025-01-01&date_to=2025-01-15",
        undefined,
      );
    });
  });

  describe("fetchAuditRecords", () => {
    it("fetches audit records with filters", async () => {
      const mockData = createAuditListResponse();
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      } as Response);

      const result = await fetchAuditRecords({
        status: "failed",
        limit: 20,
        offset: 0,
      });
      expect(result).toEqual(mockData);
      const url = vi.mocked(fetch).mock.calls[0]?.[0] as string;
      expect(url).toContain("status=failed");
      expect(url).toContain("limit=20");
    });

    it("omits 'all' status from query params", async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(createAuditListResponse()),
      } as Response);

      await fetchAuditRecords({ status: "all" });
      const url = vi.mocked(fetch).mock.calls[0]?.[0] as string;
      expect(url).not.toContain("status=");
    });
  });

  describe("fetchRules", () => {
    it("fetches rules list", async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ rules: [] }),
      } as Response);

      const result = await fetchRules();
      expect(result).toEqual([]);
      expect(fetch).toHaveBeenCalledWith("/api/rules", undefined);
    });
  });

  describe("error handling", () => {
    it("throws ApiError on non-OK response", async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.resolve({ message: "Something went wrong" }),
      } as unknown as Response);

      await expect(fetchMetrics()).rejects.toThrow(ApiError);
      await expect(fetchMetrics()).rejects.toThrow("Something went wrong");
    });

    it("falls back to statusText when JSON parse fails", async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        status: 502,
        statusText: "Bad Gateway",
        json: () => Promise.reject(new Error("parse error")),
      } as unknown as Response);

      await expect(fetchMetrics()).rejects.toThrow("Bad Gateway");
    });
  });
});
