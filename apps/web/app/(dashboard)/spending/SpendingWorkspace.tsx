/**
 * Spending Tracker (Expense Tracking) workspace.
 *
 * Three concerns:
 *   1. Add / edit / delete individual expense rows.
 *   2. Import a CSV of expenses in bulk (and export the same shape
 *      back out for backup / sharing).
 *   3. Show a per-month + per-category summary so the user can see
 *      where the money is going.
 */

"use client";

import * as React from "react";

import type {
  Expense,
  ExpenseCreate,
  ExpenseSummary,
  StudyPlan,
} from "@beyond-borders/shared-types";

import { ApiClientError } from "@/lib/client-api";
import { expensesApi } from "@/lib/expenses-api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatMoney } from "@/lib/format";

const CATEGORIES = [
  "tuition",
  "accommodation",
  "food",
  "transport",
  "utilities",
  "insurance",
  "travel",
  "visa",
  "deposits",
  "study_materials",
  "personal",
  "miscellaneous",
];

type Draft = {
  id: string | null;
  category: string;
  description: string;
  amount: string;
  currency: string;
  spent_on: string;
  plan_id: string;
  payment_method: string;
  notes: string;
};

const EMPTY: Draft = {
  id: null,
  category: "food",
  description: "",
  amount: "",
  currency: "USD",
  spent_on: new Date().toISOString().slice(0, 10),
  plan_id: "",
  payment_method: "",
  notes: "",
};

function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}

export function SpendingWorkspace({ initialPlans }: { initialPlans: StudyPlan[] }) {
  const [plans] = React.useState<StudyPlan[]>(initialPlans);
  const [expenses, setExpenses] = React.useState<Expense[]>([]);
  const [summary, setSummary] = React.useState<ExpenseSummary | null>(null);
  const [draft, setDraft] = React.useState<Draft>(EMPTY);
  const [importText, setImportText] = React.useState<string>("");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [importSummary, setImportSummary] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, sum] = await Promise.all([
        expensesApi.list({ limit: 200 }),
        expensesApi.summary(),
      ]);
      setExpenses(rows);
      setSummary(sum);
    } catch (err) {
      setError(describeError(err, "Could not load your expenses."));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  function startEdit(row: Expense) {
    setDraft({
      id: row.id,
      category: row.category,
      description: row.description ?? "",
      amount: row.amount,
      currency: row.currency,
      spent_on: row.spent_on,
      plan_id: row.plan_id ?? "",
      payment_method: row.payment_method ?? "",
      notes: row.notes ?? "",
    });
    setError(null);
    setSuccess(null);
  }

  function resetDraft() {
    setDraft(EMPTY);
    setError(null);
    setSuccess(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = draft.amount.trim();
    if (amount === "") {
      setError("Please enter an amount.");
      return;
    }
    if (draft.spent_on.trim() === "") {
      setError("Please pick a date.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      if (draft.id) {
        const updated = await expensesApi.update(draft.id, {
          category: draft.category,
          description: draft.description,
          amount,
          currency: draft.currency.toUpperCase(),
          spent_on: draft.spent_on,
          plan_id: draft.plan_id === "" ? null : draft.plan_id,
          payment_method: draft.payment_method === "" ? null : draft.payment_method,
          notes: draft.notes === "" ? null : draft.notes,
        });
        setSuccess(`Updated “${updated.description || updated.category}”.`);
      } else {
        const created = await expensesApi.create({
          category: draft.category,
          description: draft.description,
          amount,
          currency: draft.currency.toUpperCase(),
          spent_on: draft.spent_on,
          plan_id: draft.plan_id === "" ? null : draft.plan_id,
          payment_method: draft.payment_method === "" ? null : draft.payment_method,
          notes: draft.notes === "" ? null : draft.notes,
        });
        setSuccess(`Logged “${created.description || created.category}”.`);
      }
      setDraft(EMPTY);
      await reload();
    } catch (err) {
      setError(describeError(err, "Could not save the expense."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(row: Expense) {
    if (!window.confirm(`Delete this ${row.category} expense?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await expensesApi.remove(row.id);
      setSuccess("Deleted.");
      if (draft.id === row.id) setDraft(EMPTY);
      await reload();
    } catch (err) {
      setError(describeError(err, "Could not delete the expense."));
    }
  }

  async function handleImport() {
    if (importText.trim() === "") {
      setError("Paste some CSV first.");
      return;
    }
    setImporting(true);
    setError(null);
    setImportSummary(null);
    try {
      const result = await expensesApi.importCsv(importText);
      setImportSummary(
        `Imported ${result.created} row${result.created === 1 ? "" : "s"}, skipped ${result.skipped}.`,
      );
      setImportText("");
      await reload();
    } catch (err) {
      setError(describeError(err, "Could not import the CSV."));
    } finally {
      setImporting(false);
    }
  }

  async function handleExport() {
    setError(null);
    try {
      const csvText = await expensesApi.exportCsv({});
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "expenses.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setSuccess("Downloaded expenses.csv.");
    } catch (err) {
      setError(describeError(err, "Could not export the CSV."));
    }
  }

  const editing = draft.id !== null;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">Spending Tracker</h1>
        <p className="text-sm text-slate">
          Log what you actually spend — in any currency, on any plan, or as
          a standalone entry. The summary below rolls it up by month and
          category so you can see where the money is going.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>{editing ? "Edit expense" : "Log an expense"}</CardTitle>
          <CardDescription>
            Amount + currency + date are required. Everything else is optional.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit} noValidate>
            <div className="flex flex-col gap-1">
              <label htmlFor="category" className="text-xs font-medium text-slate">
                Category
              </label>
              <select
                id="category"
                className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal focus-visible:outline-none"
                value={draft.category}
                onChange={(e) => setDraft((d) => ({ ...d, category: e.target.value }))}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="amount" className="text-xs font-medium text-slate">
                Amount
              </label>
              <Input
                id="amount"
                value={draft.amount}
                onChange={(e) => setDraft((d) => ({ ...d, amount: e.target.value }))}
                placeholder="0.00"
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="currency" className="text-xs font-medium text-slate">
                Currency
              </label>
              <Input
                id="currency"
                value={draft.currency}
                onChange={(e) => setDraft((d) => ({ ...d, currency: e.target.value }))}
                placeholder="USD"
                maxLength={3}
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="spent_on" className="text-xs font-medium text-slate">
                Spent on
              </label>
              <Input
                id="spent_on"
                type="date"
                value={draft.spent_on}
                onChange={(e) => setDraft((d) => ({ ...d, spent_on: e.target.value }))}
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="plan_id" className="text-xs font-medium text-slate">
                Plan (optional)
              </label>
              <select
                id="plan_id"
                className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal focus-visible:outline-none"
                value={draft.plan_id}
                onChange={(e) => setDraft((d) => ({ ...d, plan_id: e.target.value }))}
              >
                <option value="">— No plan —</option>
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="payment_method" className="text-xs font-medium text-slate">
                Payment method
              </label>
              <Input
                id="payment_method"
                value={draft.payment_method}
                onChange={(e) => setDraft((d) => ({ ...d, payment_method: e.target.value }))}
                placeholder="Card, cash, transfer…"
                maxLength={64}
              />
            </div>
            <div className="flex flex-col gap-1 md:col-span-2">
              <label htmlFor="description" className="text-xs font-medium text-slate">
                Description (optional)
              </label>
              <Input
                id="description"
                value={draft.description}
                onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
                placeholder="Lunch at the cafeteria"
                maxLength={500}
              />
            </div>
            <div className="flex flex-col gap-1 md:col-span-3">
              <label htmlFor="notes" className="text-xs font-medium text-slate">
                Notes (optional)
              </label>
              <textarea
                id="notes"
                value={draft.notes}
                onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
                maxLength={2000}
                rows={2}
                className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-midnight placeholder:text-slate/60 focus:border-teal-dark focus:outline-none focus:ring-2 focus:ring-teal-dark/30"
              />
            </div>

            {error ? (
              <p
                role="alert"
                className="md:col-span-3 rounded-md border border-red/20 bg-red/5 px-3 py-2 text-xs text-red"
              >
                {error}
              </p>
            ) : null}
            {success ? (
              <p
                role="status"
                className="md:col-span-3 rounded-md border border-teal-dark/20 bg-mint/40 px-3 py-2 text-xs text-teal-dark"
              >
                {success}
              </p>
            ) : null}

            <div className="md:col-span-3 flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : editing ? "Save changes" : "Log expense"}
              </Button>
              {editing ? (
                <Button type="button" variant="ghost" onClick={resetDraft}>
                  Cancel
                </Button>
              ) : null}
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Summary</CardTitle>
            <CardDescription>
              {summary
                ? `${summary.count} logged expense${summary.count === 1 ? "" : "s"} · headline ${formatMoney(summary.total, summary.base_currency)}`
                : "Loading…"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {summary && summary.by_category.length > 0 ? (
              <ul className="flex flex-col divide-y divide-border">
                {summary.by_category.map((c) => (
                  <li
                    key={`${c.category}-${c.currency}`}
                    className="flex items-center justify-between py-2 first:pt-0 last:pb-0"
                  >
                    <span className="text-sm text-midnight">
                      {c.category.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm tabular-nums text-slate">
                      {formatMoney(c.total, c.currency)} · {c.count}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate">No expenses yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By month</CardTitle>
            <CardDescription>Most recent months first.</CardDescription>
          </CardHeader>
          <CardContent>
            {summary && summary.months.length > 0 ? (
              <ul className="flex flex-col divide-y divide-border">
                {summary.months.slice(0, 6).map((m) => (
                  <li
                    key={`${m.month}-${m.currency}`}
                    className="flex items-center justify-between py-2 first:pt-0 last:pb-0"
                  >
                    <span className="text-sm text-midnight">{m.month}</span>
                    <span className="text-sm tabular-nums text-slate">
                      {formatMoney(m.total, m.currency)} · {m.count}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate">No months to show yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>CSV import / export</CardTitle>
          <CardDescription>
            Paste a CSV with the columns{" "}
            <code className="rounded bg-ivory px-1">category, amount, currency, spent_on</code>{" "}
            (other columns are optional). The exporter returns the same shape.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <textarea
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            rows={6}
            className="w-full rounded-md border border-border bg-white px-3 py-2 font-mono text-xs text-midnight focus:border-teal-dark focus:outline-none focus:ring-2 focus:ring-teal-dark/30"
            placeholder={"category,amount,currency,spent_on,description\nfood,12.50,USD,2026-10-19,Coffee"}
          />
          {importSummary ? (
            <p className="mt-2 text-xs text-teal-dark">{importSummary}</p>
          ) : null}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button type="button" onClick={handleImport} disabled={importing}>
              {importing ? "Importing…" : "Import CSV"}
            </Button>
            <Button type="button" variant="secondary" onClick={handleExport}>
              Export CSV
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setImportText("")}
            >
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent expenses</CardTitle>
          <CardDescription>
            {loading
              ? "Loading…"
              : `${expenses.length} row${expenses.length === 1 ? "" : "s"} shown.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {expenses.length === 0 && !loading ? (
            <p className="text-xs text-slate">No expenses yet — log your first one above.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {expenses.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-medium text-midnight">
                      {row.description || row.category.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-slate">
                      {row.spent_on} · {row.category.replace(/_/g, " ")}
                      {row.payment_method ? ` · ${row.payment_method}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm tabular-nums text-midnight">
                      {formatMoney(row.amount, row.currency)}
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => startEdit(row)}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => handleDelete(row)}
                    >
                      Delete
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}