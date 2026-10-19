/**
 * Client for the Expense Tracking (Spending Tracker) API.
 *
 * Wraps the proxy at /api/expenses/* with typed helpers for
 * CRUD, CSV import (raw text body), CSV export (raw text body),
 * and the per-month + per-category summary.
 */

import type {
  Expense,
  ExpenseCreate,
  ExpenseImportResult,
  ExpenseSummary,
  ExpenseUpdate,
} from "@beyond-borders/shared-types";

import { apiFetch } from "@/lib/client-api";

export type ExpenseListParams = {
  plan_id?: string;
  since?: string;
  until?: string;
  limit?: number;
};

export const expensesApi = {
  list: (params: ExpenseListParams = {}) => {
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") {
        search.set(k, String(v));
      }
    }
    const qs = search.toString();
    return apiFetch<Expense[]>(`/expenses${qs ? `?${qs}` : ""}`);
  },

  create: (input: ExpenseCreate) =>
    apiFetch<Expense>("/expenses", { method: "POST", json: input }),

  update: (id: string, input: ExpenseUpdate) =>
    apiFetch<Expense>(`/expenses/${encodeURIComponent(id)}`, {
      method: "PATCH",
      json: input,
    }),

  remove: (id: string) =>
    apiFetch<void>(`/expenses/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  // CSV import: send the raw text body and read JSON back.
  importCsv: async (text: string): Promise<ExpenseImportResult> => {
    const res = await fetch("/api/expenses/import.csv", {
      method: "POST",
      headers: { "Content-Type": "text/csv; charset=utf-8" },
      body: text,
    });
    if (!res.ok) {
      const data = await res.text();
      throw new Error(data || `Import failed: ${res.status}`);
    }
    return (await res.json()) as ExpenseImportResult;
  },

  // CSV export: returns the raw text so the browser can trigger a
  // download from a Blob.
  exportCsv: async (params: { plan_id?: string } = {}): Promise<string> => {
    const search = new URLSearchParams();
    if (params.plan_id) search.set("plan_id", params.plan_id);
    const qs = search.toString();
    const res = await fetch(`/api/expenses/export.csv${qs ? `?${qs}` : ""}`);
    if (!res.ok) {
      throw new Error(`Export failed: ${res.status}`);
    }
    return res.text();
  },

  summary: (params: ExpenseListParams = {}): Promise<ExpenseSummary> => {
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") {
        search.set(k, String(v));
      }
    }
    const qs = search.toString();
    return apiFetch<ExpenseSummary>(`/expenses/summary${qs ? `?${qs}` : ""}`);
  },
};
