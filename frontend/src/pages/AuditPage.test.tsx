import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuditPage } from "./AuditPage";
import { createAuditListResponse } from "@/test/mocks";

vi.mock("@/services/api", () => ({
  fetchAuditRecords: vi.fn(),
}));

import { fetchAuditRecords } from "@/services/api";

describe("AuditPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders audit table after loading", async () => {
    const mockData = createAuditListResponse();
    vi.mocked(fetchAuditRecords).mockResolvedValue(mockData);

    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Showing 1-2 of 2")).toBeInTheDocument();
    });
  });

  it("shows error on API failure", async () => {
    vi.mocked(fetchAuditRecords).mockRejectedValue(new Error("Server error"));

    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to load audit records/),
      ).toBeInTheDocument();
    });
  });

  it("renders filter controls", async () => {
    vi.mocked(fetchAuditRecords).mockResolvedValue(createAuditListResponse());

    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("From")).toBeInTheDocument();
    expect(screen.getByText("To")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });
});
