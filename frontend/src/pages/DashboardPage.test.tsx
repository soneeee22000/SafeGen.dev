import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "./DashboardPage";
import { createMetricsResponse } from "@/test/mocks";

vi.mock("@/services/api", () => ({
  fetchMetrics: vi.fn(),
}));

// Mock recharts ResponsiveContainer which needs DOM measurements
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 800, height: 300 }}>{children}</div>
    ),
  };
});

import { fetchMetrics } from "@/services/api";

describe("DashboardPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders KPI cards after loading", async () => {
    const mockMetrics = createMetricsResponse({
      total_requests: 100,
      total_passed: 85,
      total_failed: 15,
    });
    vi.mocked(fetchMetrics).mockResolvedValue(mockMetrics);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("100")).toBeInTheDocument();
    });
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("Total Requests")).toBeInTheDocument();
  });

  it("shows error state on API failure", async () => {
    vi.mocked(fetchMetrics).mockRejectedValue(new Error("Network error"));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load metrics/)).toBeInTheDocument();
    });
  });

  it("shows loading skeletons initially", () => {
    vi.mocked(fetchMetrics).mockReturnValue(new Promise(() => {}));

    const { container } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(
      container.querySelectorAll("[data-slot='skeleton']").length,
    ).toBeGreaterThan(0);
  });
});
