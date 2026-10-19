/**
 * Tests for the Spending Tracker (Expense Tracking) workspace.
 *
 * Mocks the API client, mounts the workspace, and verifies the form,
 * the per-month / per-category summary, and the CSV import path.
 */

import * as React from "react";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SpendingWorkspace } from "@/app/(dashboard)/spending/SpendingWorkspace";
import type {
  Expense,
  ExpenseImportResult,
  ExpenseSummary,
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

const EXPENSE_A: Expense = {
  id: "22222222-2222-2222-2222-222222222222",
  user_id: "00000000-0000-0000-0000-000000000001",
  category: "food",
  description: "Coffee",
  amount: "4.50",
  currency: "USD",
  spent_on: "2026-10-19",
  plan_id: null,
  payment_method: "card",
  notes: null,
  created_at: "2026-10-19T10:00:00.000Z",
  updated_at: "2026-10-19T10:00:00.000Z",
};

const EXPENSE_B: Expense = {
  ...EXPENSE_A,
  id: "33333333-3333-3333-3333-333333333333",
  category: "transport",
  description: "Bus pass",
  amount: "30.00",
  currency: "EUR",
  spent_on: "2026-10-18",
};

const SUMMARY: ExpenseSummary = {
  base_currency: "EUR",
  total: "30.00",
  count: 2,
  months: [
    {
      month: "2026-10",
      total: "30.00",
      currency: "EUR",
      count: 1,
      by_category: [
        { category: "transport", total: "30.00", currency: "EUR", count: 1 },
      ],
    },
  ],
  by_category: [
    { category: "food", total: "4.50", currency: "USD", count: 1 },
    { category: "transport", total: "30.00", currency: "EUR", count: 1 },
  ],
};

type ListFn = (params?: object) => Promise<Expense[]>;
type CreateFn = (input: unknown) => Promise<Expense>;
type UpdateFn = (id: string, input: unknown) => Promise<Expense>;
type RemoveFn = (id: string) => Promise<void>;
type ImportFn = (text: string) => Promise<ExpenseImportResult>;
type ExportFn = (params?: object) => Promise<string>;
type SummaryFn = (params?: object) => Promise<ExpenseSummary>;

const mocks = vi.hoisted(() => ({
  list: vi.fn<ListFn>(),
  create: vi.fn<CreateFn>(),
  update: vi.fn<UpdateFn>(),
  remove: vi.fn<RemoveFn>(),
  importCsv: vi.fn<ImportFn>(),
  exportCsv: vi.fn<ExportFn>(),
  summary: vi.fn<SummaryFn>(),
}));

vi.mock("@/lib/expenses-api", () => ({
  expensesApi: {
    list: mocks.list,
    create: mocks.create,
    update: mocks.update,
    remove: mocks.remove,
    importCsv: mocks.importCsv,
    exportCsv: mocks.exportCsv,
    summary: mocks.summary,
  },
}));

describe("SpendingWorkspace", () => {
  beforeEach(() => {
    mocks.list.mockReset();
    mocks.create.mockReset();
    mocks.update.mockReset();
    mocks.remove.mockReset();
    mocks.importCsv.mockReset();
    mocks.exportCsv.mockReset();
    mocks.summary.mockReset();
    mocks.list.mockResolvedValue([EXPENSE_A, EXPENSE_B]);
    mocks.summary.mockResolvedValue(SUMMARY);
    mocks.create.mockImplementation(
      async (input: unknown): Promise<Expense> => {
        const i = input as {
          category: string;
          description: string;
          amount: string;
          currency: string;
          spent_on: string;
        };
        return {
          id: "99999999-9999-9999-9999-999999999999",
          user_id: "00000000-0000-0000-0000-000000000001",
          category: i.category,
          description: i.description,
          amount: i.amount,
          currency: i.currency,
          spent_on: i.spent_on,
          plan_id: null,
          payment_method: null,
          notes: null,
          created_at: "2026-10-19T11:00:00.000Z",
          updated_at: "2026-10-19T11:00:00.000Z",
        };
      },
    );
    mocks.update.mockImplementation(
      async (id: string, input: unknown): Promise<Expense> => ({
        ...EXPENSE_A,
        id,
        description: (input as { description?: string }).description ?? EXPENSE_A.description,
        amount: (input as { amount?: string }).amount ?? EXPENSE_A.amount,
      }),
    );
    mocks.remove.mockResolvedValue(undefined);
    mocks.importCsv.mockResolvedValue({ created: 3, skipped: 1, errors: [] });
    mocks.exportCsv.mockResolvedValue(
      "category,amount,currency,spent_on\nfood,1,USD,2026-10-19\n",
    );
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads the expense list and the summary on mount", async () => {
    render(<SpendingWorkspace initialPlans={[PLAN]} />);
    expect(screen.getByRole("heading", { name: /spending tracker/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.list).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getByText("Coffee")).toBeInTheDocument();
    });
    expect(screen.getByText("Bus pass")).toBeInTheDocument();
    // The summary "by category" lists both rows.
    expect(screen.getAllByText(/food/i).length).toBeGreaterThan(0);
  });

  it("submits the form and creates a new expense", async () => {
    render(<SpendingWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(screen.getByText("Coffee")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/amount/i), {
      target: { value: "9.99" },
    });
    fireEvent.change(screen.getByLabelText(/description/i), {
      target: { value: "Bookstore" },
    });
    fireEvent.click(screen.getByRole("button", { name: /log expense/i }));

    await waitFor(() => {
      expect(mocks.create).toHaveBeenCalledTimes(1);
    });
    const call = mocks.create.mock.calls[0]?.[0] as {
      amount: string;
      description: string;
      currency: string;
    };
    expect(call.amount).toBe("9.99");
    expect(call.description).toBe("Bookstore");
    expect(call.currency).toBe("USD");
  });

  it("imports a pasted CSV", async () => {
    render(<SpendingWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(screen.getByText("Coffee")).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/food,12\.50,USD/i);
    fireEvent.change(textarea, {
      target: { value: "category,amount,currency,spent_on\nfood,1,USD,2026-10-19\n" },
    });
    fireEvent.click(screen.getByRole("button", { name: /import csv/i }));

    await waitFor(() => {
      expect(mocks.importCsv).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getByText(/imported 3 row/i)).toBeInTheDocument();
    });
  });

  it("exports the CSV", async () => {
    render(<SpendingWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(screen.getByText("Coffee")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));
    await waitFor(() => {
      expect(mocks.exportCsv).toHaveBeenCalledTimes(1);
    });
  });

  it("deletes a row after confirm", async () => {
    render(<SpendingWorkspace initialPlans={[PLAN]} />);
    await waitFor(() => {
      expect(screen.getByText("Bus pass")).toBeInTheDocument();
    });
    const deleteButtons = screen.getAllByRole("button", { name: /^delete$/i });
    expect(deleteButtons.length).toBeGreaterThan(0);
    fireEvent.click(deleteButtons[0]!);
    await waitFor(() => {
      expect(mocks.remove).toHaveBeenCalledTimes(1);
    });
  });
});
