/**
 * Funding-plan page smoke test.
 *
 * Mocks the `paymentsApi`, `savingsGoalsApi`, `fundingPlanApi`, and the
 * pre-existing `fundingApi` clients so the workspace can mount without
 * a backend, and asserts that the summary cards and the timeline of
 * payments render with the right headlines.
 */

import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";

import { FundingPlanWorkspace } from "@/app/(dashboard)/funding-plan/FundingPlanWorkspace";

import type {
  FundingPlanSummary,
  PaymentEvent,
  SavingsGoal,
  StudyPlan,
} from "@beyond-borders/shared-types";

const PLAN_ID = "11111111-1111-1111-1111-111111111111";

const PLAN: StudyPlan = {
  id: PLAN_ID,
  name: "My plan",
  destination_country: null,
  base_currency: "USD",
  start_date: "2026-09-01",
  duration_months: 24,
  end_date: "2028-09-01",
  notes: null,
  institution_name: null,
  program_name: null,
  city: null,
  tuition_amount: null,
  tuition_currency: null,
  home_currency: "USD",
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
};

const FUNDING_SUMMARY: FundingPlanSummary = {
  plan_id: PLAN_ID,
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
};

const SAMPLE_PAYMENT: PaymentEvent = {
  id: "22222222-2222-2222-2222-222222222222",
  user_id: "33333333-3333-3333-3333-333333333333",
  plan_id: PLAN_ID,
  title: "Tuition deposit",
  category: "tuition",
  amount: "1500.0000",
  currency: "USD",
  due_date: "2026-10-30",
  display_status: "planned",
  notes: null,
  is_recurring: false,
  recurrence_frequency: null,
  recurrence_end_date: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

const SAMPLE_SAVINGS: SavingsGoal = {
  id: "44444444-4444-4444-4444-444444444444",
  user_id: "33333333-3333-3333-3333-333333333333",
  plan_id: PLAN_ID,
  name: "First year",
  target_amount: "12000.0000",
  current_amount: "2000.0000",
  currency: "USD",
  target_date: "2027-09-01",
  notes: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/funding-plan",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/payments-api", () => ({
  fundingPlanApi: {
    summary: vi.fn(async () => FUNDING_SUMMARY),
    timeline: vi.fn(async () => ({ plan_id: PLAN_ID, entries: [] })),
    convert: vi.fn(),
    exportCsvUrl: vi.fn(() => `/api/funding-plan/${PLAN_ID}/export.csv`),
  },
  paymentsApi: {
    list: vi.fn(async () => [SAMPLE_PAYMENT]),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
  savingsGoalsApi: {
    list: vi.fn(async () => [SAMPLE_SAVINGS]),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

vi.mock("@/lib/readiness-api", () => ({
  fundingApi: {
    list: vi.fn(async () => []),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
  studyPlansApi: {
    list: vi.fn(),
    create: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

describe("FundingPlanWorkspace", () => {
  it("renders summary cards and the existing payment", async () => {
    render(
      <FundingPlanWorkspace initialPlans={[PLAN]} initialPlanId={PLAN_ID} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Upcoming (30 days)")).toBeInTheDocument();
    });
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("Confirmed funding")).toBeInTheDocument();
    // The overdue note from the API bubbles up
    expect(screen.getByText(/past due/i)).toBeInTheDocument();
    // The seeded payment title appears
    expect(screen.getByText("Tuition deposit")).toBeInTheDocument();
    // The seeded savings goal appears
    expect(screen.getByText("First year")).toBeInTheDocument();
    // CSV export link is wired up
    const exportLink = screen.getByText(/Export payments \(CSV\)/i).closest("a");
    expect(exportLink).toHaveAttribute(
      "href",
      `/api/funding-plan/${PLAN_ID}/export.csv`,
    );
    expect(exportLink).toHaveAttribute("download");
  });
});