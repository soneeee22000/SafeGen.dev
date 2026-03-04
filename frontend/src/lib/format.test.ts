import { describe, expect, it } from "vitest";
import {
  daysAgo,
  formatDate,
  formatDuration,
  formatScore,
  scoreBgColor,
  scoreColor,
} from "./format";

describe("formatScore", () => {
  it("formats 0.85 as 85.0%", () => {
    expect(formatScore(0.85)).toBe("85.0%");
  });

  it("formats 1.0 as 100.0%", () => {
    expect(formatScore(1.0)).toBe("100.0%");
  });

  it("formats 0 as 0.0%", () => {
    expect(formatScore(0)).toBe("0.0%");
  });
});

describe("formatDuration", () => {
  it("formats ms under 1000 as ms", () => {
    expect(formatDuration(245)).toBe("245ms");
  });

  it("formats ms over 1000 as seconds", () => {
    expect(formatDuration(1500)).toBe("1.5s");
  });

  it("formats 0ms", () => {
    expect(formatDuration(0)).toBe("0ms");
  });
});

describe("formatDate", () => {
  it("formats ISO date to locale string", () => {
    const result = formatDate("2025-01-15T10:30:00Z");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
    expect(result).toContain("2025");
  });
});

describe("daysAgo", () => {
  it("returns Today for current date", () => {
    const now = new Date().toISOString();
    expect(daysAgo(now)).toBe("Today");
  });

  it("returns Yesterday for 1 day ago", () => {
    const yesterday = new Date(Date.now() - 86400000).toISOString();
    expect(daysAgo(yesterday)).toBe("Yesterday");
  });

  it("returns Xd ago for older dates", () => {
    const daysBack = new Date(Date.now() - 3 * 86400000).toISOString();
    expect(daysAgo(daysBack)).toBe("3d ago");
  });
});

describe("scoreColor", () => {
  it("returns green for high scores", () => {
    expect(scoreColor(0.9)).toContain("green");
  });

  it("returns amber for medium scores", () => {
    expect(scoreColor(0.6)).toContain("amber");
  });

  it("returns red for low scores", () => {
    expect(scoreColor(0.3)).toContain("red");
  });
});

describe("scoreBgColor", () => {
  it("returns green bg for high scores", () => {
    expect(scoreBgColor(0.9)).toContain("green");
  });

  it("returns amber bg for medium scores", () => {
    expect(scoreBgColor(0.6)).toContain("amber");
  });

  it("returns red bg for low scores", () => {
    expect(scoreBgColor(0.3)).toContain("red");
  });
});
