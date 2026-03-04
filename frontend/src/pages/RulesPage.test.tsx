import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RulesPage } from "./RulesPage";
import { createRuleDocument } from "@/test/mocks";

vi.mock("@/services/api", () => ({
  fetchRules: vi.fn(),
  ingestRuleFile: vi.fn(),
}));

import { fetchRules } from "@/services/api";

describe("RulesPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders rule list after loading", async () => {
    const rules = [
      createRuleDocument({ filename: "gdpr.md", chunk_count: 5 }),
      createRuleDocument({ filename: "pii.md", chunk_count: 3 }),
    ];
    vi.mocked(fetchRules).mockResolvedValue(rules);

    render(
      <MemoryRouter>
        <RulesPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("gdpr.md")).toBeInTheDocument();
    });
    expect(screen.getByText("pii.md")).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    vi.mocked(fetchRules).mockRejectedValue(new Error("Fetch failed"));

    render(
      <MemoryRouter>
        <RulesPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load rules/)).toBeInTheDocument();
    });
  });

  it("renders upload zone", async () => {
    vi.mocked(fetchRules).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <RulesPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Browse files")).toBeInTheDocument();
  });
});
