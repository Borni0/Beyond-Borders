import { describe, expect, it } from "vitest";

import { formatMoney, formatDate, toDateInputValue } from "@/lib/format";

describe("format", () => {
  it("formats money in the requested currency", () => {
    expect(formatMoney(1234, "USD")).toMatch(/\$1,234/);
    expect(formatMoney(0, "EUR")).toMatch(/€0/);
  });

  it("formats dates in a human-readable form", () => {
    expect(formatDate("2026-10-19T00:00:00Z")).toMatch(/Oct/);
  });

  it("emits YYYY-MM-DD for date inputs", () => {
    expect(toDateInputValue("2026-10-19T00:00:00Z")).toBe("2026-10-19");
    expect(toDateInputValue(null)).toBe("");
    expect(toDateInputValue("not-a-date")).toBe("");
  });
});
