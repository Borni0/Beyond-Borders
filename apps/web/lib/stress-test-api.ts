/**
 * Client for the Stress Test (Financial Weather) API.
 *
 * Endpoints (all proxied through Next.js so the cookie stays
 * same-origin):
 *
 *   GET    /stress-test/presets
 *   GET    /stress-test/scenarios
 *   POST   /stress-test/scenarios
 *   GET    /stress-test/scenarios/{id}
 *   PATCH  /stress-test/scenarios/{id}
 *   DELETE /stress-test/scenarios/{id}
 *   POST   /stress-test/run
 */

import type {
  StressRunRequest,
  StressRunResult,
  StressScenario,
  StressScenarioCreate,
  StressScenarioKey,
  StressScenarioUpdate,
} from "@beyond-borders/shared-types";

import { apiFetch } from "@/lib/client-api";

export type StressPreset = {
  label: string;
  description: string;
  default_adjustment: {
    type: string;
    value: string | null;
    note: string | null;
  };
};

export type StressPresetMap = Record<StressScenarioKey, StressPreset>;

export const stressTestApi = {
  presets: () =>
    apiFetch<{ presets: StressPresetMap }>("/stress-test/presets"),

  listScenarios: (planId?: string) => {
    const qs = planId
      ? `?plan_id=${encodeURIComponent(planId)}`
      : "";
    return apiFetch<StressScenario[]>(`/stress-test/scenarios${qs}`);
  },

  createScenario: (input: StressScenarioCreate) =>
    apiFetch<StressScenario>("/stress-test/scenarios", {
      method: "POST",
      json: input,
    }),

  updateScenario: (id: string, input: StressScenarioUpdate) =>
    apiFetch<StressScenario>(
      `/stress-test/scenarios/${encodeURIComponent(id)}`,
      { method: "PATCH", json: input },
    ),

  removeScenario: (id: string) =>
    apiFetch<void>(`/stress-test/scenarios/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  run: (input: StressRunRequest) =>
    apiFetch<StressRunResult>("/stress-test/run", {
      method: "POST",
      json: input,
    }),
};
