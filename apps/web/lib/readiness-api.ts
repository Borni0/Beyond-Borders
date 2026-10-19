/**
 * Client for the study plan + readiness API. All calls go through the
 * same-origin Next.js proxy under /api/*, which forwards to FastAPI.
 */

import type {
  CostItem,
  CostItemCreate,
  CostItemUpdate,
  ExchangeRate,
  ExchangeRateUpsert,
  FundingSource,
  FundingSourceCreate,
  FundingSourceUpdate,
  ReadinessResult,
  StudyPlan,
  StudyPlanCreate,
  StudyPlanUpdate,
} from "@beyond-borders/shared-types";

import { apiFetch } from "@/lib/client-api";

export const studyPlansApi = {
  list: () => apiFetch<StudyPlan[]>("/study-plans"),
  create: (input: StudyPlanCreate) =>
    apiFetch<StudyPlan>("/study-plans", { method: "POST", json: input }),
  get: (id: string) => apiFetch<StudyPlan>(`/study-plans/${id}`),
  update: (id: string, input: StudyPlanUpdate) =>
    apiFetch<StudyPlan>(`/study-plans/${id}`, {
      method: "PATCH",
      json: input,
    }),
  remove: (id: string) =>
    apiFetch<void>(`/study-plans/${id}`, { method: "DELETE" }),
};

export const costsApi = {
  list: (planId: string) =>
    apiFetch<CostItem[]>(`/costs/${planId}`),
  create: (planId: string, input: CostItemCreate) =>
    apiFetch<CostItem>(`/costs/${planId}`, { method: "POST", json: input }),
  update: (planId: string, costId: string, input: CostItemUpdate) =>
    apiFetch<CostItem>(`/costs/${planId}/${costId}`, {
      method: "PATCH",
      json: input,
    }),
  remove: (planId: string, costId: string) =>
    apiFetch<void>(`/costs/${planId}/${costId}`, { method: "DELETE" }),
};

export const fundingApi = {
  list: (planId: string) =>
    apiFetch<FundingSource[]>(`/funding/${planId}`),
  create: (planId: string, input: FundingSourceCreate) =>
    apiFetch<FundingSource>(`/funding/${planId}`, {
      method: "POST",
      json: input,
    }),
  update: (planId: string, sourceId: string, input: FundingSourceUpdate) =>
    apiFetch<FundingSource>(`/funding/${planId}/${sourceId}`, {
      method: "PATCH",
      json: input,
    }),
  remove: (planId: string, sourceId: string) =>
    apiFetch<void>(`/funding/${planId}/${sourceId}`, { method: "DELETE" }),
};

export const fxApi = {
  list: () => apiFetch<ExchangeRate[]>("/fx"),
  upsert: (input: ExchangeRateUpsert) =>
    apiFetch<ExchangeRate>("/fx", { method: "PUT", json: input }),
};

export const readinessApi = {
  get: (planId: string) =>
    apiFetch<ReadinessResult>(`/readiness/${planId}`),
};
