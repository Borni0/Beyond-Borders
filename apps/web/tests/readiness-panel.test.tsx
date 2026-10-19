/**
 * Tests for the ReadinessPanel presentation. The component is pure
 * (props in, rendered output out), so we feed it canned
 * ReadinessResult objects and assert the headline numbers and chips
 * appear.
 */

import * as React from "react";
import { render, screen } from "@testing-library/react";

import { ReadinessPanel } from "@/components/readiness/ReadinessPanel";

import type { ReadinessResult } from "@beyond-borders/shared-types";

const FULL_RESULT: ReadinessResult = {
  plan_id: "p1",
  base_currency: "USD",
  breakdown: {
    base_currency: "USD",
    per_year: [
      {
        year_index: 1,
        recurring_total: "10800.00",
        one_time_total: "15000.00",
        total: "25800.00",
      },
      {
        year_index: 2,
        recurring_total: "10800.00",
        one_time_total: "0.00",
        total: "10800.00",
      },
    ],
    first_year_cost: "25800.00",
    total_projected_cost: "36600.00",
    refundable_deposits: "2000.00",
    per_category: {
      tuition: "15000.00",
      accommodation: "21600.00",
    },
  },
  funding: {
    base_currency: "USD",
    confirmed_total: "20000.00",
    conditional_total: "5000.00",
    expected_total: "0.00",
    unavailable_total: "0.00",
    eligible_confirmed: "20000.00",
    eligible_with_conditional: "25000.00",
    available_before_departure: "20000.00",
  },
  funding_gap: "16600.00",
  funding_surplus: "0.00",
  upfront_cash_requirement: "22800.00",
  upfront_cash_gap: "2800.00",
  upfront_cash_window_days: 30,
  statuses: [
    "funding_gap_identified",
    "conditional_funding",
    "scenario_sensitive",
  ],
  missing_inputs: [],
  notes: ["Scenario sensitivity is not yet modeled."],
  first_year_funding_gap: "5800.00",
  coverage_pct: "68.31",
  potential_gap_after_expected: "5000.00",
};

describe("ReadinessPanel", () => {
  it("renders the headline stats including first-year cost, coverage, and the secondary gap cards", () => {
    render(<ReadinessPanel result={FULL_RESULT} />);
    expect(screen.getByTestId("first-year-cost")).toHaveTextContent(
      "$25,800.00",
    );
    expect(screen.getByTestId("total-cost")).toHaveTextContent("$36,600.00");
    expect(screen.getByTestId("funding-gap")).toHaveTextContent("$16,600.00");
    expect(screen.getByTestId("coverage-pct")).toHaveTextContent("68.3%");
    expect(screen.getByTestId("upfront-gap")).toHaveTextContent("$2,800.00");
    expect(screen.getByTestId("first-year-funding-gap")).toHaveTextContent(
      "$5,800.00",
    );
    expect(screen.getByTestId("potential-gap")).toHaveTextContent(
      "$5,000.00",
    );
  });

  it("renders a transparent checklist derived from the result", () => {
    render(<ReadinessPanel result={FULL_RESULT} />);
    const checklist = screen.getByTestId("readiness-checklist");
    expect(checklist).toHaveTextContent(/confirmed funding/i);
    expect(checklist).toHaveTextContent(/first-year cost/i);
    expect(checklist).toHaveTextContent(/upfront window/i);
  });

  it("renders every status chip from the result", () => {
    render(<ReadinessPanel result={FULL_RESULT} />);
    const chips = screen.getByTestId("status-chips");
    expect(chips).toHaveTextContent("Funding gap");
    expect(chips).toHaveTextContent("Conditional funding");
    expect(chips).toHaveTextContent("Scenario sensitivity");
  });

  it("renders a per-year breakdown table", () => {
    render(<ReadinessPanel result={FULL_RESULT} />);
    expect(screen.getByText("Year 1")).toBeInTheDocument();
    expect(screen.getByText("Year 2")).toBeInTheDocument();
  });

  it("renders notes when present", () => {
    render(<ReadinessPanel result={FULL_RESULT} />);
    expect(
      screen.getByText(/scenario sensitivity is not yet modeled/i),
    ).toBeInTheDocument();
  });

  it("shows the zero-gap case in green", () => {
    const zero: ReadinessResult = {
      ...FULL_RESULT,
      funding_gap: "0.00",
      funding_surplus: "600.00",
      upfront_cash_gap: "0.00",
      statuses: ["no_modeled_shortfall", "scenario_sensitive"],
    };
    render(<ReadinessPanel result={zero} />);
    expect(screen.getByText("No modeled shortfall")).toBeInTheDocument();
    expect(screen.getByText(/Surplus/)).toBeInTheDocument();
  });
});
