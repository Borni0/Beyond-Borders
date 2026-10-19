/**
 * Display-time label/description for each readiness status code.
 * Keep in sync with backend `ReadinessStatusCode` enum.
 */

import type { ReadinessStatusCode } from "@beyond-borders/shared-types";

export interface StatusMeta {
  code: ReadinessStatusCode;
  label: string;
  description: string;
  tone: "ok" | "warn" | "danger" | "info" | "muted";
}

export const STATUS_META: Record<ReadinessStatusCode, StatusMeta> = {
  no_modeled_shortfall: {
    code: "no_modeled_shortfall",
    label: "No modeled shortfall",
    description: "All modeled needs are covered by confirmed funding.",
    tone: "ok",
  },
  funding_gap_identified: {
    code: "funding_gap_identified",
    label: "Funding gap",
    description:
      "Confirmed funding does not cover the projected total cost.",
    tone: "danger",
  },
  upfront_cash_gap: {
    code: "upfront_cash_gap",
    label: "Upfront cash gap",
    description:
      "Cash available before departure is below the next 30 days of need.",
    tone: "warn",
  },
  conditional_funding: {
    code: "conditional_funding",
    label: "Conditional funding",
    description:
      "Some funding depends on conditions (scholarship, expected income, etc.).",
    tone: "warn",
  },
  scenario_sensitive: {
    code: "scenario_sensitive",
    label: "Scenario sensitivity",
    description:
      "Phase 2 will let you stress-test exchange rates, rent, and scholarships.",
    tone: "muted",
  },
  needs_more_information: {
    code: "needs_more_information",
    label: "Needs more information",
    description:
      "Add at least one cost, one confirmed funding source, and any required FX rates.",
    tone: "info",
  },
};
