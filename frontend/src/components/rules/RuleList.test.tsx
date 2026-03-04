import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RuleList } from "./RuleList";
import { createRuleDocument } from "@/test/mocks";

describe("RuleList", () => {
  it("renders rule cards", () => {
    const rules = [
      createRuleDocument({ filename: "gdpr_rules.md", chunk_count: 5 }),
      createRuleDocument({ filename: "pii_rules.md", chunk_count: 3 }),
    ];
    render(<RuleList rules={rules} />);
    expect(screen.getByText("gdpr_rules.md")).toBeInTheDocument();
    expect(screen.getByText("pii_rules.md")).toBeInTheDocument();
    expect(screen.getByText("5 chunks")).toBeInTheDocument();
    expect(screen.getByText("3 chunks")).toBeInTheDocument();
  });

  it("shows empty state when no rules", () => {
    render(<RuleList rules={[]} />);
    expect(
      screen.getByText(
        "No rules ingested yet. Upload a document to get started.",
      ),
    ).toBeInTheDocument();
  });
});
