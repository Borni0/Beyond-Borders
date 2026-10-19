/**
 * Client for the Decision Studio API.
 *
 * All routes are proxied through Next.js to the FastAPI backend at
 * `/api/v1/decision-studio/...`. The proxy lives at
 * `/api/decision-studio/...` so the cookie domain stays same-origin.
 */

import type {
  CompareRequest,
  CompareResult,
  SavedComparisonCreate,
  SavedComparisonDetail,
  SavedComparisonPublic,
  SavedComparisonUpdate,
} from "@beyond-borders/shared-types";

import { apiFetch } from "@/lib/client-api";

export const decisionStudioApi = {
  compare: (input: CompareRequest) =>
    apiFetch<CompareResult>("/decision-studio/compare", {
      method: "POST",
      json: input,
    }),

  listSaved: () =>
    apiFetch<SavedComparisonPublic[]>("/decision-studio/comparisons"),

  createSaved: (input: SavedComparisonCreate) =>
    apiFetch<SavedComparisonPublic>("/decision-studio/comparisons", {
      method: "POST",
      json: input,
    }),

  openSaved: (id: string) =>
    apiFetch<SavedComparisonDetail>(
      `/decision-studio/comparisons/${encodeURIComponent(id)}`,
    ),

  updateSaved: (id: string, input: SavedComparisonUpdate) =>
    apiFetch<SavedComparisonPublic>(
      `/decision-studio/comparisons/${encodeURIComponent(id)}`,
      { method: "PATCH", json: input },
    ),

  removeSaved: (id: string) =>
    apiFetch<void>(`/decision-studio/comparisons/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
};
