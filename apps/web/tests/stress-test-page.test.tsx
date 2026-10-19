/**
 * Tests for the Stress Test (Financial Weather) workspace.
 *
 * Mocks the API client, mounts the workspace with one plan, and
 * verifies:
 *   * the preset catalogue loads and the form is ready;
 *   * the run button calls the API with the inline adjustment;
 *   * a saved scenario is listed and can be re-run by id;
 *   * the result panel shows the baseline/scenario/delta columns.
 */

import * as React from "react";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { StressTestWorkspace } from "@/app/(dashboard)/stress-test/StressTestWorkspace";
import type {
  StressRunResult,
  StressScenario,
  StudyPlan,
} from "@beyond-borders/shared-types";

const PLAN_ID = "11111111-1111-1111-1111-111111111111";

const PLAN: StudyPlan = {
  id: PLAN_ID,
  name: "MSc Berlin",
  destination_country: "DE",
  base_currency: "EUR",
  start_date: "2026-09-01",
  duration_months: 24,
  end_date: "2028-09-01",
  notes: null,
  institution_name: "TU Berlin",
  program_name: "MSc CS",
  city: "Berlin",
  tuition_amount: "1000.00",
  tuition_currency: "EUR",
  home_currency: "EUR",
  created_at: "2026-10-19T10:00:00.000Z",
  updated_at: "2026-10-19T10:00:00.000Z",
};

const PRESETS = {
  rent_shock: {
    label: "Rent shock",
    description: "+25% rent & utilities",
    default_adjustment: { type: "rent_increase_pct", value: "25", note: null },
  },
  scholarship_cut: {
    label: "Scholarship cut",
    description: "−25% scholarships",
    default_adjustment: {
      type: "scholarship_reduction_pct",
      value: "25",
      note: null,
    },
  },
  fx_shock: {
    label: "FX shock (informational)",
    description: "FX −10% (informational)",
    default_adjustment: { type: "fx_shift_pct", value: "10", note: null },
  },
  family_delay: {
    label: "Family support delay",
    description: "Family +60 days",
    default_adjustment: {
      type: "family_support_delay_days",
      value: "60",
      note: null,
    },
  },
  custom: {
    label: "Custom scenario",
    description: "Build your own combination",
    default_adjustment: { type: "custom_note", value: null, note: "" },
  },
};

const SAVED_SCENARIO: StressScenario = {
  id: "99999999-9999-9999-9999-999999999999",
  user_id: "00000000-0000-0000-0000-000000000001",
  plan_id: PLAN_ID,
  name: "Big rent shock",
  scenario_key: "rent_shock",
  adjustments: [{ type: "rent_increase_pct", value: "40", note: null }],
  notes: null,
  created_at: "2026-10-19T10:00:00.000Z",
  updated_at: "2026-10-19T10:00:00.000Z",
};

const RESULT: StressRunResult = {
  plan_id: PLAN_ID,
  base_currency: "EUR",
  scenario_id: null,
  scenario_name: "Rent shock",
  upfront_window_days: 30,
  funding_gap: { baseline: "1000.00", scenario: "1500.00", delta: "500.00" },
  funding_surplus: { baseline: "0.00", scenario: "0.00", delta: "0.00" },
  upfront_cash_requirement: {
    baseline: "2000.00",
    scenario: "2500.00",
    delta: "500.00",
  },
  upfront_cash_gap: { baseline: "0.00", scenario: "500.00", delta: "500.00" },
  first_year_cost: {
    baseline: "20000.00",
    scenario: "22000.00",
    delta: "2000.00",
  },
  total_projected_cost: {
    baseline: "40000.00",
    scenario: "44000.00",
    delta: "4000.00",
  },
  eligible_confirmed: {
    baseline: "15000.00",
    scenario: "15000.00",
    delta: "0.00",
  },
  eligible_with_conditional: {
    baseline: "20000.00",
    scenario: "20000.00",
    delta: "0.00",
  },
  available_before_departure: {
    baseline: "12000.00",
    scenario: "12000.00",
    delta: "0.00",
  },
  notes: ["baseline plan unchanged"],
  warnings: ["Funding gap worsens by 500.00 EUR in the scenario."],
  statuses_baseline: ["funding_gap_identified"],
  statuses_scenario: ["funding_gap_identified", "upfront_cash_gap"],
  generated_at: "2026-10-19T12:00:00.000Z",
  calculation_version: "stress_test_v1",
};

type PresetsFn = () => Promise<{ presets: typeof PRESETS }>;
type ListFn = (planId?: string) => Promise<StressScenario[]>;
type CreateFn = (input: unknown) => Promise<StressScenario>;
type RemoveFn = (id: string) => Promise<void>;
type RunFn = (input: unknown) => Promise<StressRunResult>;

const mocks = vi.hoisted(() => ({
  presets: vi.fn<PresetsFn>(),
  listScenarios: vi.fn<ListFn>(),
  createScenario: vi.fn<CreateFn>(),
  removeScenario: vi.fn<RemoveFn>(),
  run: vi.fn<RunFn>(),
}));

vi.mock("@/lib/stress-test-api", () => ({
  stressTestApi: {
    presets: mocks.presets,
    listScenarios: mocks.listScenarios,
    createScenario: mocks.createScenario,
    removeScenario: mocks.removeScenario,
    run: mocks.run,
  },
}));

describe("StressTestWorkspace", () => {
  beforeEach(() => {
    mocks.presets.mockReset();
    mocks.listScenarios.mockReset();
    mocks.createScenario.mockReset();
    mocks.removeScenario.mockReset();
    mocks.run.mockReset();
    mocks.presets.mockResolvedValue({ presets: PRESETS });
    mocks.listScenarios.mockResolvedValue([SAVED_SCENARIO]);
    mocks.createScenario.mockImplementation(async (input: unknown) => {
      const i = input as {
        name: string;
        scenario_key: keyof typeof PRESETS;
        adjustments: StressScenario["adjustments"];
        notes?: string | null;
      };
      return {
        id: "new-scenario",
        user_id: "00000000-0000-0000-0000-000000000001",
        plan_id: PLAN_ID,
        name: i.name,
        scenario_key: i.scenario_key,
        adjustments: i.adjustments,
        notes: i.notes ?? null,
        created_at: "2026-10-19T11:00:00.000Z",
        updated_at: "2026-10-19T11:00:00.000Z",
      };
    });
    mocks.removeScenario.mockResolvedValue(undefined);
    mocks.run.mockResolvedValue(RESULT);
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads the preset catalogue and renders the form on mount", async () => {
    render(<StressTestWorkspace initialPlans={[PLAN]} />);
    expect(screen.getByRole("heading", { name: /stress test/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.presets).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(mocks.listScenarios).toHaveBeenCalledWith(PLAN_ID);
    });
    expect(screen.getByText("Big rent shock")).toBeInTheDocument();
  });

  it("runs the scenario with the inline adjustment", async () => {
    render(<StressTestWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(mocks.presets).toHaveBeenCalledTimes(1);
    });
    fireEvent.click(screen.getByRole("button", { name: /run scenario/i }));
    await waitFor(() => {
      expect(mocks.run).toHaveBeenCalledTimes(1);
    });
    const call = mocks.run.mock.calls[0]?.[0] as {
      plan_id: string;
      adjustments: Array<{ type: string; value: string }>;
    };
    expect(call.plan_id).toBe(PLAN_ID);
    expect(call.adjustments[0]?.type).toBe("rent_increase_pct");
  });

  it("re-runs a saved scenario when the user picks it", async () => {
    render(<StressTestWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(screen.getByText("Big rent shock")).toBeInTheDocument();
    });
    // Use the saved scenario.
    const useButtons = screen.getAllByRole("button", { name: /^use$/i });
    expect(useButtons.length).toBeGreaterThan(0);
    fireEvent.click(useButtons[0]!);
    fireEvent.click(screen.getByRole("button", { name: /run scenario/i }));
    await waitFor(() => {
      expect(mocks.run).toHaveBeenCalledTimes(1);
    });
    const call = mocks.run.mock.calls[0]?.[0] as {
      plan_id: string;
      scenario_id: string;
    };
    expect(call.scenario_id).toBe(SAVED_SCENARIO.id);
  });

  it("renders the result panel after a successful run", async () => {
    render(<StressTestWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(mocks.presets).toHaveBeenCalledTimes(1);
    });
    fireEvent.click(screen.getByRole("button", { name: /run scenario/i }));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /scenario result/i }),
      ).toBeInTheDocument();
    });
    expect(screen.getAllByText(/funding gap/i).length).toBeGreaterThan(0);
    // The warnings strip surfaces the gap-worsens message.
    expect(
      screen.getByText(/funding gap worsens by 500\.00 eur/i),
    ).toBeInTheDocument();
  });
});
