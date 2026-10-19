/**
 * Phase 2 schema tests: prove the shared Zod schemas accept the shapes
 * the API returns and reject obvious garbage. This is the cheapest test
 * we can run without standing up the backend.
 */

import { describe, expect, it } from "vitest";

import {
  convertResponseSchema,
  fundingBucketSchema,
  fundingPlanSummarySchema,
  paymentEventSchema,
  paymentStatusDisplayEnum,
  savingsBucketSchema,
  savingsGoalSchema,
  timelineEntrySchema,
} from "@beyond-borders/shared-types";

describe("Phase 2 shared schemas", () => {
  it("accepts a payment event from the API", () => {
    const ok = paymentEventSchema.safeParse({
      id: "11111111-1111-1111-1111-111111111111",
      user_id: "11111111-1111-1111-1111-111111111111",
      plan_id: "22222222-2222-2222-2222-222222222222",
      title: "Tuition deposit",
      category: "tuition",
      amount: "500.0000",
      currency: "USD",
      due_date: "2026-10-19",
      display_status: "planned",
      notes: null,
      is_recurring: false,
      recurrence_frequency: null,
      recurrence_end_date: null,
      created_at: "2026-10-19T00:00:00Z",
      updated_at: "2026-10-19T00:00:00Z",
    });
    expect(ok.success).toBe(true);
  });

  it("rejects a payment event whose display_status is not allowed", () => {
    const bad = paymentEventSchema.safeParse({
      id: "11111111-1111-1111-1111-111111111111",
      user_id: "11111111-1111-1111-1111-111111111111",
      plan_id: null,
      title: "x",
      category: "tuition",
      amount: "1.0",
      currency: "USD",
      due_date: "2026-10-19",
      display_status: "nonsense",
      notes: null,
      is_recurring: false,
      recurrence_frequency: null,
      recurrence_end_date: null,
      created_at: "2026-10-19T00:00:00Z",
      updated_at: "2026-10-19T00:00:00Z",
    });
    expect(bad.success).toBe(false);
  });

  it("display status enum includes overdue", () => {
    expect(paymentStatusDisplayEnum.options).toContain("overdue");
  });

  it("accepts a savings goal", () => {
    const ok = savingsGoalSchema.safeParse({
      id: "11111111-1111-1111-1111-111111111111",
      user_id: "11111111-1111-1111-1111-111111111111",
      plan_id: null,
      name: "First year",
      target_amount: "12000.0000",
      current_amount: "1500.0000",
      currency: "USD",
      target_date: "2027-09-01",
      notes: null,
      created_at: "2026-10-19T00:00:00Z",
      updated_at: "2026-10-19T00:00:00Z",
    });
    expect(ok.success).toBe(true);
  });

  it("accepts a funding-plan summary", () => {
    const ok = fundingPlanSummarySchema.safeParse({
      plan_id: "11111111-1111-1111-1111-111111111111",
      base_currency: "USD",
      buckets: [
        {
          currency: "USD",
          total: "15000.0000",
          confirmed: "10000.0000",
          conditional: "5000.0000",
          expected: "0.0000",
          unavailable: "0.0000",
        },
      ],
      savings_buckets: [
        {
          currency: "USD",
          target_total: "12000.0000",
          current_total: "2000.0000",
        },
      ],
      upcoming_payments: "1500.0000",
      overdue_payments: "200.0000",
      upcoming_payments_count: 1,
      overdue_payments_count: 1,
      payments_by_currency: { USD: "1700.0000" },
      notes: ["1 payment(s) are past due."],
    });
    expect(ok.success).toBe(true);
  });

  it("accepts a timeline entry", () => {
    const ok = timelineEntrySchema.safeParse({
      event_id: "11111111-1111-1111-1111-111111111111",
      title: "Monthly rent",
      category: "accommodation",
      amount: "800.0000",
      currency: "USD",
      due_date: "2026-10-05",
      display_status: "planned",
      plan_id: "22222222-2222-2222-2222-222222222222",
      is_recurring: true,
    });
    expect(ok.success).toBe(true);
  });

  it("accepts a convert response", () => {
    const ok = convertResponseSchema.safeParse({
      from_currency: "USD",
      to_currency: "EUR",
      from_amount: "1000.0000",
      converted_amount: "900.0000",
      fee_pct: "0.0100",
      fee_amount: "9.0000",
      total_cost: "909.0000",
      rate_used: "0.90000000",
      rate_type: "user_entered",
    });
    expect(ok.success).toBe(true);
  });

  it("funding and savings bucket schemas round-trip minimal data", () => {
    expect(
      fundingBucketSchema.safeParse({
        currency: "USD",
        total: "0",
        confirmed: "0",
        conditional: "0",
        expected: "0",
        unavailable: "0",
      }).success,
    ).toBe(true);
    expect(
      savingsBucketSchema.safeParse({
        currency: "USD",
        target_total: "0",
        current_total: "0",
      }).success,
    ).toBe(true);
  });
});
