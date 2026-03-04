import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { PlaygroundPage } from "./PlaygroundPage";
import { createValidateResponse } from "@/test/mocks";

vi.mock("@/services/api", () => ({
  validatePrompt: vi.fn(),
}));

import { validatePrompt } from "@/services/api";

function renderPage() {
  return render(
    <MemoryRouter>
      <PlaygroundPage />
    </MemoryRouter>,
  );
}

describe("PlaygroundPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders empty state on mount", () => {
    renderPage();
    expect(
      screen.getByText("Enter a prompt and click Validate to test compliance."),
    ).toBeInTheDocument();
  });

  it("renders prompt textarea", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Enter a prompt to validate..."),
    ).toBeInTheDocument();
  });

  it("renders example prompt buttons", () => {
    renderPage();
    expect(screen.getByText("Clean")).toBeInTheDocument();
    expect(screen.getByText("PII Leak")).toBeInTheDocument();
    expect(screen.getByText("Mixed")).toBeInTheDocument();
    expect(screen.getByText("Try:")).toBeInTheDocument();
  });

  it("clicking example fills textarea", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("PII Leak"));

    const textarea = screen.getByPlaceholderText(
      "Enter a prompt to validate...",
    ) as HTMLTextAreaElement;
    expect(textarea.value).toContain("john.doe@company.com");
  });

  it("renders category toggles", () => {
    renderPage();
    expect(screen.getByLabelText("Toggle PII")).toBeInTheDocument();
    expect(screen.getByLabelText("Toggle Bias")).toBeInTheDocument();
    expect(screen.getByLabelText("Toggle Safety")).toBeInTheDocument();
  });

  it("submit calls validatePrompt with correct payload", async () => {
    const user = userEvent.setup();
    const mockResponse = createValidateResponse();
    vi.mocked(validatePrompt).mockResolvedValue(mockResponse);

    renderPage();

    const textarea = screen.getByPlaceholderText(
      "Enter a prompt to validate...",
    );
    await user.type(textarea, "Test prompt");
    await user.click(screen.getByText("Validate"));

    await waitFor(() => {
      expect(validatePrompt).toHaveBeenCalledWith({
        prompt: "Test prompt",
        rules_category: "all",
      });
    });
  });

  it("shows loading skeleton during submission", async () => {
    const user = userEvent.setup();
    let resolve: (v: ReturnType<typeof createValidateResponse>) => void;
    const promise = new Promise<ReturnType<typeof createValidateResponse>>(
      (r) => {
        resolve = r;
      },
    );
    vi.mocked(validatePrompt).mockReturnValue(promise);

    renderPage();

    const textarea = screen.getByPlaceholderText(
      "Enter a prompt to validate...",
    );
    await user.type(textarea, "Test prompt");
    await user.click(screen.getByText("Validate"));

    expect(screen.getByTestId("result-skeleton")).toBeInTheDocument();

    resolve!(createValidateResponse());
    await waitFor(() => {
      expect(screen.queryByTestId("result-skeleton")).not.toBeInTheDocument();
    });
  });

  it("renders result with flags", async () => {
    const user = userEvent.setup();
    const mockResponse = createValidateResponse({
      compliance: {
        passed: false,
        score: 0.4,
        flags: [
          {
            layer: "pii",
            severity: "critical",
            message: "Email address detected",
            details: {},
          },
          {
            layer: "bias",
            severity: "warning",
            message: "Gendered term found",
            details: {},
          },
        ],
        layers_run: ["pii", "bias", "safety"],
      },
    });
    vi.mocked(validatePrompt).mockResolvedValue(mockResponse);

    renderPage();

    await user.type(
      screen.getByPlaceholderText("Enter a prompt to validate..."),
      "Test",
    );
    await user.click(screen.getByText("Validate"));

    await waitFor(() => {
      expect(screen.getByText("40.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Email address detected")).toBeInTheDocument();
    expect(screen.getByText("Gendered term found")).toBeInTheDocument();
  });

  it("renders clean result", async () => {
    const user = userEvent.setup();
    vi.mocked(validatePrompt).mockResolvedValue(createValidateResponse());

    renderPage();

    await user.type(
      screen.getByPlaceholderText("Enter a prompt to validate..."),
      "Clean prompt",
    );
    await user.click(screen.getByText("Validate"));

    await waitFor(() => {
      expect(screen.getByText("100.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("Passed")).toBeInTheDocument();
    expect(screen.queryByText(/Flags \(/)).not.toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    const user = userEvent.setup();
    vi.mocked(validatePrompt).mockRejectedValue(new Error("Network error"));

    renderPage();

    await user.type(
      screen.getByPlaceholderText("Enter a prompt to validate..."),
      "Test",
    );
    await user.click(screen.getByText("Validate"));

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("validate button is disabled when textarea is empty", () => {
    renderPage();
    const button = screen.getByText("Validate");
    expect(button).toBeDisabled();
  });

  it("renders layers run", async () => {
    const user = userEvent.setup();
    vi.mocked(validatePrompt).mockResolvedValue(createValidateResponse());

    renderPage();

    await user.type(
      screen.getByPlaceholderText("Enter a prompt to validate..."),
      "Test",
    );
    await user.click(screen.getByText("Validate"));

    await waitFor(() => {
      expect(
        screen.getByText("Layers run: pii, bias, safety"),
      ).toBeInTheDocument();
    });
  });
});
