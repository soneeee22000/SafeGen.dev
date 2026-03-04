import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuditTable } from "./AuditTable";
import { createAuditRecord } from "@/test/mocks";

describe("AuditTable", () => {
  it("renders rows for each record", () => {
    const records = [
      createAuditRecord({ request_id: "r1" }),
      createAuditRecord({ request_id: "r2", compliance_passed: false }),
    ];
    render(<AuditTable records={records} onRowClick={vi.fn()} />);
    expect(screen.getByText("Passed")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("shows empty state when no records", () => {
    render(<AuditTable records={[]} onRowClick={vi.fn()} />);
    expect(screen.getByText("No audit records found.")).toBeInTheDocument();
  });

  it("calls onRowClick when a row is clicked", async () => {
    const user = userEvent.setup();
    const record = createAuditRecord();
    const onRowClick = vi.fn();

    render(<AuditTable records={[record]} onRowClick={onRowClick} />);
    await user.click(screen.getByText("Passed"));
    expect(onRowClick).toHaveBeenCalledWith(record);
  });

  it("renders prompt text truncated", () => {
    const record = createAuditRecord({ prompt: "My test prompt" });
    render(<AuditTable records={[record]} onRowClick={vi.fn()} />);
    expect(screen.getByText("My test prompt")).toBeInTheDocument();
  });
});
