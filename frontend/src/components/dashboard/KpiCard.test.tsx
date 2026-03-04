import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Activity } from "lucide-react";
import { KpiCard } from "./KpiCard";

describe("KpiCard", () => {
  it("renders title and value", () => {
    render(<KpiCard title="Total Requests" value="100" icon={Activity} />);
    expect(screen.getByText("Total Requests")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("renders optional description", () => {
    render(
      <KpiCard
        title="Passed"
        value="85"
        icon={Activity}
        description="85% compliance"
      />,
    );
    expect(screen.getByText("85% compliance")).toBeInTheDocument();
  });

  it("does not render description when not provided", () => {
    const { container } = render(
      <KpiCard title="Failed" value="15" icon={Activity} />,
    );
    expect(container.querySelectorAll("p")).toHaveLength(0);
  });
});
