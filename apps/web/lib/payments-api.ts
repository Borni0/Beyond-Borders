/**
 * Client for the Phase 2 endpoints: payment events, savings goals, and
 * the funding-plan aggregate. All calls go through the same-origin
 * Next.js proxy under /api/*.
 */

import type {
  ConvertRequest,
  ConvertResponse,
  FundingPlanSummary,
  FundingPlanTimeline,
  PaymentEvent,
  PaymentEventCreate,
  PaymentEventUpdate,
  SavingsGoal,
  SavingsGoalCreate,
  SavingsGoalUpdate,
} from "@beyond-borders/shared-types";

import { apiFetch } from "@/lib/client-api";

export const paymentsApi = {
  list: (params?: { plan_id?: string }) => {
    const qs = params?.plan_id
      ? `?plan_id=${encodeURIComponent(params.plan_id)}`
      : "";
    return apiFetch<PaymentEvent[]>(`/payments${qs}`);
  },
  create: (input: PaymentEventCreate) =>
    apiFetch<PaymentEvent>("/payments", { method: "POST", json: input }),
  update: (id: string, input: PaymentEventUpdate) =>
    apiFetch<PaymentEvent>(`/payments/${id}`, {
      method: "PATCH",
      json: input,
    }),
  remove: (id: string) =>
    apiFetch<void>(`/payments/${id}`, { method: "DELETE" }),
};

export const savingsGoalsApi = {
  list: (params?: { plan_id?: string }) => {
    const qs = params?.plan_id
      ? `?plan_id=${encodeURIComponent(params.plan_id)}`
      : "";
    return apiFetch<SavingsGoal[]>(`/savings-goals${qs}`);
  },
  create: (input: SavingsGoalCreate) =>
    apiFetch<SavingsGoal>("/savings-goals", { method: "POST", json: input }),
  update: (id: string, input: SavingsGoalUpdate) =>
    apiFetch<SavingsGoal>(`/savings-goals/${id}`, {
      method: "PATCH",
      json: input,
    }),
  remove: (id: string) =>
    apiFetch<void>(`/savings-goals/${id}`, { method: "DELETE" }),
};

export const fundingPlanApi = {
  summary: (planId: string) =>
    apiFetch<FundingPlanSummary>(`/funding-plan/${planId}/summary`),
  timeline: (planId: string) =>
    apiFetch<FundingPlanTimeline>(`/funding-plan/${planId}/timeline`),
  convert: (planId: string, input: ConvertRequest) =>
    apiFetch<ConvertResponse>(`/funding-plan/${planId}/convert`, {
      method: "POST",
      json: input,
    }),
  exportCsvUrl: (planId: string) => `/api/funding-plan/${planId}/export.csv`,
};
