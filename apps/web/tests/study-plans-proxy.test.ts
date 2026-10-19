import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { resolveDatalistValue } from "../app/(dashboard)/readiness/ReadinessWorkspace";

describe("study plans proxy route", () => {
  it("normalizes a country label from the dropdown to the API code", () => {
    const value = resolveDatalistValue("United Kingdom", [
      { value: "GB", label: "United Kingdom" },
      { value: "US", label: "United States" },
    ]);

    expect(value).toBe("GB");
  });

  it("handles calls to /api/study-plans without a dynamic subpath", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          id: "plan-123",
          name: "Test Plan",
          destination_country: "US",
          base_currency: "USD",
          start_date: "2025-01-15",
          duration_months: 12,
          end_date: "2026-01-15",
          notes: null,
          institution_name: "Test University",
          program_name: "MBA",
          city: "Boston",
          tuition_amount: 30000,
          tuition_currency: "USD",
          home_currency: "USD",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await import("../app/api/study-plans/route");
    const req = new NextRequest("http://localhost/api/study-plans", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: "Test Plan",
        destination_country: "US",
        base_currency: "USD",
        start_date: "2025-01-15",
        duration_months: 12,
        institution_name: "Test University",
        program_name: "MBA",
        city: "Boston",
        tuition_amount: 30000,
        tuition_currency: "USD",
        home_currency: "USD",
      }),
    });

    const res = await POST(req, { params: Promise.resolve({}) });

    expect(res.status).toBe(201);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/study-plans",
      expect.objectContaining({ method: "POST" }),
    );
    await expect(res.json()).resolves.toMatchObject({ id: "plan-123", name: "Test Plan" });

    vi.unstubAllGlobals();
  });

  it("supports the real Next.js static-route invocation without a context argument", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ id: "plan-456", name: "Static Route Plan" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await import("../app/api/study-plans/route");
    const req = new NextRequest("http://localhost/api/study-plans", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: "Static Route Plan",
        destination_country: "GB",
        base_currency: "USD",
        start_date: "2025-01-15",
        duration_months: 12,
        institution_name: "Oxford",
        program_name: "MSc",
        city: "London",
        tuition_amount: 25000,
        tuition_currency: "GBP",
        home_currency: "USD",
      }),
    });

    const res = await POST(req, undefined as any);

    expect(res.status).toBe(201);
    await expect(res.json()).resolves.toMatchObject({ id: "plan-456" });

    vi.unstubAllGlobals();
  });
});
