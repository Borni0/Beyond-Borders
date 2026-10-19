/**
 * Timeline page smoke test: with a mocked API, the workspace groups
 * entries into month buckets and renders the filter pills.
 */

import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";

import { TimelineWorkspace } from "@/app/(dashboard)/timeline/TimelineWorkspace";

import type {
  FundingPlanTimeline,
  PaymentEvent,
  StudyPlan,
  TimelineEntry,
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

const ENTRIES: TimelineEntry[] = [
  {
    event_id: "e1",
    title: "Tuition deposit",
    category: "tuition",
    amount: "1500.0000",
    currency: "USD",
    due_date: "2026-10-15",
    display_status: "planned",
    plan_id: PLAN_ID,
    is_recurring: false,
  },
  {
    event_id: "e2",
    title: "Late visa fee",
    category: "visa",
    amount: "200.0000",
    currency: "USD",
    due_date: "2026-09-20",
    display_status: "overdue",
    plan_id: PLAN_ID,
    is_recurring: false,
  },
];

const TIMELINE: FundingPlanTimeline = { plan_id: PLAN_ID, entries: ENTRIES };

const PAYMENT: PaymentEvent = {
  id: "e1",
  user_id: "u",
  plan_id: PLAN_ID,
  title: "Tuition deposit",
  category: "tuition",
  amount: "1500.0000",
  currency: "USD",
  due_date: "2026-10-15",
  display_status: "planned",
  notes: null,
  is_recurring: false,
  recurrence_frequency: null,
  recurrence_end_date: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/timeline",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/payments-api", () => ({
  fundingPlanApi: {
    summary: vi.fn(),
    timeline: vi.fn(async () => TIMELINE),
    convert: vi.fn(),
    exportCsvUrl: vi.fn(),
  },
  paymentsApi: {
    list: vi.fn(async () => [PAYMENT]),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
  savingsGoalsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

describe("TimelineWorkspace", () => {
  it("groups entries by month and shows filter pills", async () => {
    render(
      <TimelineWorkspace initialPlans={[PLAN]} initialPlanId={PLAN_ID} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Upcoming payments")).toBeInTheDocument();
    });

    // Both entries render with their titles (each may appear twice — once
    // in the chronological list, once in the "all events" panel).
    expect(screen.getAllByText("Tuition deposit").length).toBeGreaterThan(0);
    expect(screen.getByText("Late visa fee")).toBeInTheDocument();

    // Month group headings
    expect(screen.getByText("October 2026")).toBeInTheDocument();
    expect(screen.getByText("September 2026")).toBeInTheDocument();

    // Filter pills include all statuses
    for (const label of ["all", "overdue", "planned", "scheduled", "paid", "cancelled"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });
});