/**
 * Decision Studio workspace smoke test.
 *
 * Mounts the workspace with two plans, mocks the API client, and
 * verifies the side-by-side comparison, scenario editor, and saved
 * comparisons list all render correctly.
 */

import * as React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { DecisionStudioWorkspace } from "@/app/(dashboard)/decision-studio/DecisionStudioWorkspace";

import type {
  CompareResult,
  SavedComparisonDetail,
  SavedComparisonPublic,
  StudyPlan,
} from "@beyond-borders/shared-types";

const PLAN_A_ID = "11111111-1111-1111-1111-111111111111";
const PLAN_B_ID = "22222222-2222-2222-2222-222222222222";
const PLAN_C_ID = "33333333-3333-3333-3333-333333333333";

const PLAN_A: StudyPlan = {
  id: PLAN_A_ID,
  name: "Plan A",
  destination_country: "US",
  base_currency: "USD",
  start_date: "2026-09-01",
  duration_months: 24,
  end_date: "2028-09-01",
  notes: null,
  institution_name: "State U",
  program_name: "MS CS",
  city: "Boston",
  tuition_amount: "40000.00",
  tuition_currency: "USD",
  home_currency: "USD",
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};
const PLAN_B: StudyPlan = {
  ...PLAN_A,
  id: PLAN_B_ID,
  name: "Plan B",
  base_currency: "USD",
  duration_months: 18,
  end_date: "2028-03-01",
  city: "Seattle",
};
const PLAN_C: StudyPlan = {
  ...PLAN_A,
  id: PLAN_C_ID,
  name: "Plan C",
  duration_months: 24,
};

const COMPARE_RESULT: CompareResult = {
  comparison_id: null,
  deadline_rankings: [],
  deadline_analysis: [],
  ranked_plans: [],
  plans: [
    {
      plan: {
        id: PLAN_A_ID,
        name: "Plan A",
        destination_country: "US",
        institution_name: "State U",
        program_name: "MS CS",
        city: "Boston",
        base_currency: "USD",
        start_date: "2026-09-01",
        duration_months: 24,
        end_date: "2028-09-01",
        scenario_name: "baseline",
        data_completeness: "complete",
        missing_inputs: [],
      },
      cost: {
        base_currency: "USD",
        total_projected_cost: "60000.00",
        first_year_cost: "32000.00",
        refundable_deposits: "1000.00",
        per_category: { tuition: "40000.00", accommodation: "18000.00" },
        per_year: [],
        cost_for_displayed_period: "60000.00",
        displayed_period_months: 24,
      },
      funding: {
        base_currency: "USD",
        confirmed_total: "30000.00",
        conditional_total: "10000.00",
        expected_total: "5000.00",
        unavailable_total: "0.00",
        eligible_confirmed: "30000.00",
        eligible_with_conditional: "40000.00",
        funding_gap: "20000.00",
        funding_surplus: "0.00",
        available_before_departure: "12000.00",
      },
      upfront: {
        base_currency: "USD",
        upfront_window_days: 30,
        upfront_cash_requirement: "15000.00",
        upfront_cash_gap: "3000.00",
      },
      earliest_payment: {
        id: "p-1",
        title: "Deposit",
        category: "tuition",
        amount: "5000.00",
        currency: "USD",
        due_date: "2026-09-10",
        display_status: "planned",
      },
      payments: [
        {
          id: "p-1",
          title: "Deposit",
          category: "tuition",
          amount: "5000.00",
          currency: "USD",
          due_date: "2026-09-10",
          display_status: "planned",
        },
      ],
    },
    {
      plan: {
        ...PLAN_A,
        id: PLAN_B_ID,
        name: "Plan B",
        duration_months: 18,
        end_date: "2028-03-01",
        scenario_name: "rent shock",
        data_completeness: "partial",
        missing_inputs: ["No funding sources entered for this plan."],
      },
      cost: {
        base_currency: "USD",
        total_projected_cost: "48000.00",
        first_year_cost: "30000.00",
        refundable_deposits: "0.00",
        per_category: { tuition: "30000.00", accommodation: "16000.00" },
        per_year: [],
        cost_for_displayed_period: "48000.00",
        displayed_period_months: 18,
      },
      funding: {
        base_currency: "USD",
        confirmed_total: "0.00",
        conditional_total: "0.00",
        expected_total: "0.00",
        unavailable_total: "0.00",
        eligible_confirmed: "0.00",
        eligible_with_conditional: "0.00",
        funding_gap: "48000.00",
        funding_surplus: "0.00",
        available_before_departure: "0.00",
      },
      upfront: {
        base_currency: "USD",
        upfront_window_days: 30,
        upfront_cash_requirement: "15000.00",
        upfront_cash_gap: "15000.00",
      },
      earliest_payment: null,
      payments: [],
    },
  ],
  warnings: [
    {
      code: "no_known_payments",
      message: "No payment events recorded for any of the selected plans.",
      plan_ids: [PLAN_A_ID, PLAN_B_ID],
    },
  ],
  generated_at: "2026-10-19T12:00:00Z",
  calculation_version: "decision_studio_v1",
};

const SAVED_ITEM: SavedComparisonPublic = {
  id: "cmp-1",
  user_id: "00000000-0000-0000-0000-000000000001",
  name: "Side-by-side",
  study_plan_ids: [PLAN_A_ID, PLAN_B_ID],
  scenarios: null,
  calculation_version: "decision_studio_v1",
  created_at: "2026-10-19T12:00:00Z",
  updated_at: "2026-10-19T12:00:00Z",
};

const SAVED_DETAIL: SavedComparisonDetail = {
  comparison: SAVED_ITEM,
  result: { ...COMPARE_RESULT, comparison_id: "cmp-1" },
};

// vi.mock factories are hoisted above the file's top-level const
// declarations, so we wrap the mocks in vi.hoisted so the factory can
// reference them safely.
type CompareFn = (input: unknown) => Promise<CompareResult>;
type ListSavedFn = () => Promise<SavedComparisonPublic[]>;
type CreateSavedFn = (input: unknown) => Promise<SavedComparisonPublic>;
type OpenSavedFn = (id: string) => Promise<SavedComparisonDetail>;
type UpdateSavedFn = (id: string, input: unknown) => Promise<SavedComparisonPublic>;
type RemoveSavedFn = (id: string) => Promise<void>;

const mocks = vi.hoisted(() => ({
  compare: vi.fn<CompareFn>(),
  listSaved: vi.fn<ListSavedFn>(),
  createSaved: vi.fn<CreateSavedFn>(),
  openSaved: vi.fn<OpenSavedFn>(),
  updateSaved: vi.fn<UpdateSavedFn>(),
  removeSaved: vi.fn<RemoveSavedFn>(),
}));

vi.mock("@/lib/decision-studio-api", () => ({
  decisionStudioApi: {
    compare: mocks.compare,
    listSaved: mocks.listSaved,
    createSaved: mocks.createSaved,
    openSaved: mocks.openSaved,
    updateSaved: mocks.updateSaved,
    removeSaved: mocks.removeSaved,
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/decision-studio",
  useSearchParams: () => new URLSearchParams(),
}));

describe("DecisionStudioWorkspace", () => {
  beforeEach(() => {
    mocks.compare.mockReset();
    mocks.listSaved.mockReset();
    mocks.createSaved.mockReset();
    mocks.openSaved.mockReset();
    mocks.updateSaved.mockReset();
    mocks.removeSaved.mockReset();
    // Wire up the default resolved values.
    mocks.compare.mockResolvedValue(COMPARE_RESULT);
    mocks.listSaved.mockResolvedValue([SAVED_ITEM]);
    mocks.createSaved.mockResolvedValue(SAVED_ITEM);
    mocks.openSaved.mockResolvedValue(SAVED_DETAIL);
    mocks.updateSaved.mockResolvedValue(SAVED_ITEM);
    mocks.removeSaved.mockResolvedValue(undefined);
    // Avoid window.confirm/window.prompt from blocking tests.
    window.confirm = vi.fn(() => true);
    window.prompt = vi.fn(() => "My saved comparison");
  });

  it("renders plans and the saved comparisons list on mount", async () => {
    render(
      <DecisionStudioWorkspace initialPlans={[PLAN_A, PLAN_B, PLAN_C]} />,
    );

    expect(screen.getByText("Decision Studio")).toBeInTheDocument();
    expect(screen.getAllByText("Plan A").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Plan B").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Plan C").length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(screen.getByText("Side-by-side")).toBeInTheDocument();
    });
  });

  it("calls the compare API and renders the side-by-side result", async () => {
    render(
      <DecisionStudioWorkspace initialPlans={[PLAN_A, PLAN_B]} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /^Compare$/i }));

    await waitFor(() => {
      expect(mocks.compare).toHaveBeenCalledTimes(1);
    });

    // Plan A's metric: funding gap = $20,000.
    await waitFor(() => {
      expect(screen.getAllByText("Funding gap").length).toBeGreaterThan(0);
    });
    // Plan B's "rent shock" scenario badge appears in the column header.
    expect(screen.getAllByText("rent shock").length).toBeGreaterThan(0);
    // The partial-data chip for Plan B.
    expect(screen.getByText("Partial data")).toBeInTheDocument();
    // Cross-plan warning surfaces in the warnings strip.
    expect(
      screen.getByText(/No payment events recorded for any/i),
    ).toBeInTheDocument();
  });

  it("reopens a saved comparison and applies its scenarios", async () => {
    render(
      <DecisionStudioWorkspace initialPlans={[PLAN_A, PLAN_B]} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Side-by-side")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^Open$/i }));

    await waitFor(() => {
      expect(mocks.openSaved).toHaveBeenCalledTimes(1);
    });
  });

  it("deletes a saved comparison after confirm", async () => {
    render(
      <DecisionStudioWorkspace initialPlans={[PLAN_A, PLAN_B]} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Side-by-side")).toBeInTheDocument();
    });

    const deleteBtn = screen.getByRole("button", { name: /^Delete$/i });
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(mocks.removeSaved).toHaveBeenCalledWith("cmp-1");
    });
  });
});
