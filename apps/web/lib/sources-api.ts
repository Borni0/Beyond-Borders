/**
 * Client for the Data Source registry (Sources & Assumptions).
 *
 * The backend already implements `/api/v1/sources` (CRUD per-user, not
 * per-plan) — this is just a thin browser wrapper around that proxy.
 *
 * Each source is a label + optional URL + optional notes, used to cite
 * where a cost, FX rate, or scholarship number came from. Sources are
 * global to the user, so the same "Stanford tuition page" can be
 * referenced from multiple cost items across multiple plans.
 */

import type {
  DataSource,
  DataSourceCreate,
  DataSourceUpdate,
} from "@beyond-borders/shared-types";

import { apiFetch } from "@/lib/client-api";

export const sourcesApi = {
  list: () => apiFetch<DataSource[]>("/sources"),
  create: (input: DataSourceCreate) =>
    apiFetch<DataSource>("/sources", { method: "POST", json: input }),
  update: (id: string, input: DataSourceUpdate) =>
    apiFetch<DataSource>(`/sources/${encodeURIComponent(id)}`, {
      method: "PATCH",
      json: input,
    }),
  remove: (id: string) =>
    apiFetch<void>(`/sources/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
};
