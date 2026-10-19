"use client";

/**
 * Funding Plan workspace.
 *
 * The student picks a plan, sees the funding + savings + payments summary
 * in one screen, and can add:
 *   - funding sources (existing flow from /readiness)
 *   - savings goals with target amount + target date
 *   - payment events with due date, amount, currency, category, status
 *   - a one-shot conversion preview from the FX table
 *
 * All state is local; the page refetches the summary whenever any
 * underlying list changes. CSV export is a simple `<a download>` to the
 * proxy route.
 */

import * as React from "react";
import { Plus, Trash2, Download, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";
import { fundingApi, studyPlansApi } from "@/lib/readiness-api";
import { fundingPlanApi, paymentsApi, savingsGoalsApi } from "@/lib/payments-api";
import { ApiClientError } from "@/lib/client-api";
import { formatDate, formatMoney } from "@/lib/format";

import type {
  FundingPlanSummary,
  FundingSource,
  FundingSourceCreate,
  FundingStatus,
  FundingType,
  PaymentCategory,
  PaymentEvent,
  PaymentEventCreate,
  PaymentStatus,
  RecurrenceFrequency,
  SavingsBucket,
  SavingsGoal,
  SavingsGoalCreate,
  StudyPlan,
} from "@beyond-borders/shared-types";

interface Props {
  initialPlans: StudyPlan[];
  initialPlanId: string | null;
}

const FUNDING_TYPES: FundingType[] = [
  "savings", "family", "scholarship", "loan", "income", "other",
];
const FUNDING_STATUSES: FundingStatus[] = [
  "confirmed", "conditional", "expected", "unavailable",
];
const PAYMENT_CATEGORIES: PaymentCategory[] = [
  "tuition", "accommodation", "food", "transport", "utilities",
  "insurance", "travel", "visa", "deposits", "study_materials",
  "personal", "miscellaneous",
];
const PAYMENT_STATUSES: PaymentStatus[] = [
  "planned", "scheduled", "paid", "cancelled",
];
const RECURRENCE_FREQUENCIES: RecurrenceFrequency[] = [
  "monthly", "quarterly", "semester", "annual",
];

export function FundingPlanWorkspace({ initialPlans, initialPlanId }: Props) {
  const [plans] = React.useState<StudyPlan[]>(initialPlans);
  const [activePlanId, setActivePlanId] = React.useState<string | null>(
    initialPlanId,
  );
  const [funding, setFunding] = React.useState<FundingSource[]>([]);
  const [savings, setSavings] = React.useState<SavingsGoal[]>([]);
  const [payments, setPayments] = React.useState<PaymentEvent[]>([]);
  const [summary, setSummary] = React.useState<FundingPlanSummary | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const activePlan = plans.find((p) => p.id === activePlanId) ?? null;

  const refresh = React.useCallback(
    async (planId: string) => {
      setError(null);
      try {
        const [f, sg, pay, s] = await Promise.all([
          fundingApi.list(planId),
          savingsGoalsApi.list({ plan_id: planId }),
          paymentsApi.list({ plan_id: planId }),
          fundingPlanApi.summary(planId),
        ]);
        setFunding(f);
        setSavings(sg);
        setPayments(pay);
        setSummary(s);
      } catch (err) {
        setError(errorMessage(err, "Could not load funding plan."));
      }
    },
    [],
  );

  React.useEffect(() => {
    if (activePlanId) {
      void refresh(activePlanId);
    } else {
      setFunding([]);
      setSavings([]);
      setPayments([]);
      setSummary(null);
    }
  }, [activePlanId, refresh]);

  // ---- Funding CRUD ----
  const addFunding = async (input: FundingSourceCreate) => {
    if (!activePlan) return;
    setBusy(true);
    try {
      const created = await fundingApi.create(activePlan.id, input);
      setFunding((prev) => [...prev, created]);
      await refresh(activePlan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not add funding source."));
    } finally {
      setBusy(false);
    }
  };
  const removeFunding = async (id: string) => {
    if (!activePlan) return;
    setBusy(true);
    try {
      await fundingApi.remove(activePlan.id, id);
      setFunding((prev) => prev.filter((f) => f.id !== id));
      await refresh(activePlan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not remove funding source."));
    } finally {
      setBusy(false);
    }
  };

  // ---- Savings CRUD ----
  const addSavingsGoal = async (input: SavingsGoalCreate) => {
    if (!activePlan) return;
    setBusy(true);
    try {
      const created = await savingsGoalsApi.create(input);
      setSavings((prev) => [...prev, created]);
      await refresh(activePlan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not add savings goal."));
    } finally {
      setBusy(false);
    }
  };
  const removeSavingsGoal = async (id: string) => {
    if (!activePlan) return;
    setBusy(true);
    try {
      await savingsGoalsApi.remove(id);
      setSavings((prev) => prev.filter((s) => s.id !== id));
      await refresh(activePlan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not remove savings goal."));
    } finally {
      setBusy(false);
    }
  };

  // ---- Payments CRUD ----
  const addPayment = async (input: PaymentEventCreate) => {
    if (!activePlan) return;
    setBusy(true);
    try {
      const created = await paymentsApi.create(input);
      setPayments((prev) => [...prev, created]);
      await refresh(activePlan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not add payment."));
    } finally {
      setBusy(false);
    }
  };
  const removePayment = async (id: string) => {
    if (!activePlan) return;
    setBusy(true);
    try {
      await paymentsApi.remove(id);
      setPayments((prev) => prev.filter((p) => p.id !== id));
      await refresh(activePlan.id);
    } catch (err) {
      setError(errorMessage(err, "Could not remove payment."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <PlanPicker
        plans={plans}
        activePlanId={activePlanId}
        onSelect={setActivePlanId}
      />

      {activePlan ? (
        <>
          {summary ? <SummaryCards summary={summary} /> : null}

          <div className="grid gap-6 lg:grid-cols-2">
            <FundingEditor
              funding={funding}
              baseCurrency={activePlan.base_currency}
              onAdd={addFunding}
              onRemove={removeFunding}
              busy={busy}
            />
            <SavingsGoalsEditor
              goals={savings}
              buckets={summary?.savings_buckets ?? []}
              baseCurrency={activePlan.base_currency}
              onAdd={addSavingsGoal}
              onRemove={removeSavingsGoal}
              busy={busy}
              defaultPlanId={activePlan.id}
            />
          </div>

          <PaymentsEditor
            payments={payments}
            baseCurrency={activePlan.base_currency}
            onAdd={addPayment}
            onRemove={removePayment}
            busy={busy}
            defaultPlanId={activePlan.id}
          />

          <ConverterCard planId={activePlan.id} />

          <div className="flex justify-end">
            <a
              href={`/api/funding-plan/${activePlan.id}/export.csv`}
              download
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-white px-3 text-sm font-medium text-midnight hover:bg-ivory"
            >
              <Download className="h-4 w-4" /> Export payments (CSV)
            </a>
          </div>
        </>
      ) : (
        <Card>
          <CardContent>
            <p className="text-sm text-slate">
              Create a study plan on the{" "}
              <a className="text-teal underline" href="/readiness">
                Readiness
              </a>{" "}
              page to start a funding plan.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message ?? fallback;
  if (err instanceof Error) return err.message;
  return fallback;
}

// ---------- Sub-components ----------

function PlanPicker({
  plans,
  activePlanId,
  onSelect,
}: {
  plans: StudyPlan[];
  activePlanId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Plans</CardTitle>
        <p className="text-sm text-slate">
          Pick a plan to manage its funding, savings goals, and payments.
        </p>
      </CardHeader>
      <CardContent>
        {plans.length === 0 ? (
          <p className="text-sm text-slate">
            No plans yet — create one on the Readiness page.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {plans.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onSelect(p.id)}
                  className={
                    "rounded-lg border px-3 py-1.5 text-sm transition-colors " +
                    (p.id === activePlanId
                      ? "border-teal bg-mint/40 text-midnight"
                      : "border-border bg-white text-slate hover:bg-ivory")
                  }
                >
                  {p.name}
                  <span className="ml-1 text-xs text-slate">({p.base_currency})</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryCards({ summary }: { summary: FundingPlanSummary }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>Upcoming (30 days)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold tabular-nums text-midnight">
            {formatMoney(summary.upcoming_payments, summary.base_currency)}
          </p>
          <p className="text-xs text-slate">
            {summary.upcoming_payments_count} payment(s) due soon
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Overdue</CardTitle>
        </CardHeader>
        <CardContent>
          <p
            className={
              "text-3xl font-semibold tabular-nums " +
              (summary.overdue_payments_count > 0 ? "text-red" : "text-midnight")
            }
          >
            {formatMoney(summary.overdue_payments, summary.base_currency)}
          </p>
          <p className="text-xs text-slate">
            {summary.overdue_payments_count} payment(s) past due
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Confirmed funding</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.buckets.length === 0 ? (
            <p className="text-sm text-slate">No funding yet.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm tabular-nums">
              {summary.buckets.map((b) => (
                <li key={b.currency} className="flex justify-between">
                  <span className="text-slate">{b.currency}</span>
                  <span className="font-medium text-midnight">
                    {formatMoney(b.confirmed, b.currency)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FundingEditor({
  funding,
  baseCurrency,
  onAdd,
  onRemove,
  busy,
}: {
  funding: FundingSource[];
  baseCurrency: string;
  onAdd: (input: FundingSourceCreate) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  busy: boolean;
}) {
  const [name, setName] = React.useState("Family savings");
  const [type, setType] = React.useState<FundingType>("savings");
  const [amount, setAmount] = React.useState("");
  const [currency, setCurrency] = React.useState(baseCurrency);
  const [status, setStatus] = React.useState<FundingStatus>("confirmed");

  React.useEffect(() => setCurrency(baseCurrency), [baseCurrency]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Funding sources</CardTitle>
        <p className="text-sm text-slate">
          Confirmed sources count against the gap; conditional and expected
          only when they land.
        </p>
      </CardHeader>
      <CardContent>
        {funding.length === 0 ? (
          <p className="text-sm text-slate">No funding sources yet.</p>
        ) : (
          <ul className="mb-4 flex flex-col gap-2">
            {funding.map((s) => (
              <li
                key={s.id}
                className="flex items-center justify-between rounded border border-border/60 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-midnight">{s.name}</span>
                  <span className="ml-2 text-slate">
                    {formatMoney(s.amount, s.currency)} · {s.status}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(s.id)}
                  className="text-slate hover:text-red"
                  aria-label={`Remove ${s.name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <form
          className="grid gap-3 sm:grid-cols-5"
          onSubmit={async (e) => {
            e.preventDefault();
            await onAdd({
              name,
              funding_type: type,
              amount,
              currency: currency.toUpperCase(),
              status,
            });
            setAmount("");
          }}
        >
          <Field label="Name" htmlFor="fn-name" required>
            <Input id="fn-name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Type" htmlFor="fn-type">
            <select
              id="fn-type"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={type}
              onChange={(e) => setType(e.target.value as FundingType)}
            >
              {FUNDING_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field label="Amount" htmlFor="fn-amt" required>
            <Input
              id="fn-amt"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
            />
          </Field>
          <Field label="Currency" htmlFor="fn-ccy" required>
            <Input
              id="fn-ccy"
              maxLength={3}
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Status" htmlFor="fn-status">
            <select
              id="fn-status"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value as FundingStatus)}
            >
              {FUNDING_STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
          <div className="col-span-full flex justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              <Plus className="h-4 w-4" /> Add funding
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function SavingsGoalsEditor({
  goals,
  buckets,
  baseCurrency,
  onAdd,
  onRemove,
  busy,
  defaultPlanId,
}: {
  goals: SavingsGoal[];
  buckets: SavingsBucket[];
  baseCurrency: string;
  onAdd: (input: SavingsGoalCreate) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  busy: boolean;
  defaultPlanId: string;
}) {
  const [name, setName] = React.useState("First year expenses");
  const [target, setTarget] = React.useState("");
  const [current, setCurrent] = React.useState("");
  const [currency, setCurrency] = React.useState(baseCurrency);
  const [targetDate, setTargetDate] = React.useState("");

  React.useEffect(() => setCurrency(baseCurrency), [baseCurrency]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Savings goals</CardTitle>
        <p className="text-sm text-slate">
          Target amount and target date for what you&apos;re saving toward.
        </p>
      </CardHeader>
      <CardContent>
        {buckets.length > 0 ? (
          <ul className="mb-4 grid gap-2 sm:grid-cols-2">
            {buckets.map((b) => {
              const tgt = Number(b.target_total);
              const cur = Number(b.current_total);
              const pct = tgt > 0 ? Math.min(100, Math.round((cur / tgt) * 100)) : 0;
              return (
                <li
                  key={b.currency}
                  className="rounded border border-border/60 p-3 text-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-slate">{b.currency}</span>
                    <span className="text-xs text-slate">{pct}%</span>
                  </div>
                  <p className="mt-1 text-base font-semibold tabular-nums text-midnight">
                    {formatMoney(b.current_total, b.currency)}{" "}
                    <span className="text-slate text-sm font-normal">
                      / {formatMoney(b.target_total, b.currency)}
                    </span>
                  </p>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded bg-ivory">
                    <div
                      className="h-full bg-teal"
                      style={{ width: `${pct}%` }}
                      aria-hidden="true"
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        ) : null}

        {goals.length === 0 ? (
          <p className="text-sm text-slate">No savings goals yet.</p>
        ) : (
          <ul className="mb-4 flex flex-col gap-2">
            {goals.map((g) => (
              <li
                key={g.id}
                className="flex items-center justify-between rounded border border-border/60 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-midnight">{g.name}</span>
                  <span className="ml-2 text-slate">
                    {formatMoney(g.current_amount, g.currency)} / {formatMoney(g.target_amount, g.currency)} by {formatDate(g.target_date)}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(g.id)}
                  className="text-slate hover:text-red"
                  aria-label={`Remove ${g.name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <form
          className="grid gap-3 sm:grid-cols-5"
          onSubmit={async (e) => {
            e.preventDefault();
            await onAdd({
              name,
              target_amount: target,
              current_amount: current || "0",
              currency: currency.toUpperCase(),
              target_date: targetDate,
              plan_id: defaultPlanId,
            });
            setTarget("");
            setCurrent("");
            setTargetDate("");
          }}
        >
          <Field label="Name" htmlFor="sg-name" required>
            <Input id="sg-name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Target amount" htmlFor="sg-tgt" required>
            <Input
              id="sg-tgt"
              inputMode="decimal"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="0.00"
            />
          </Field>
          <Field label="Current saved" htmlFor="sg-cur">
            <Input
              id="sg-cur"
              inputMode="decimal"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              placeholder="0.00"
            />
          </Field>
          <Field label="Currency" htmlFor="sg-ccy" required>
            <Input
              id="sg-ccy"
              maxLength={3}
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Target date" htmlFor="sg-date" required>
            <Input
              id="sg-date"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </Field>
          <div className="col-span-full flex justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              <Plus className="h-4 w-4" /> Add goal
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function PaymentsEditor({
  payments,
  baseCurrency,
  onAdd,
  onRemove,
  busy,
  defaultPlanId,
}: {
  payments: PaymentEvent[];
  baseCurrency: string;
  onAdd: (input: PaymentEventCreate) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  busy: boolean;
  defaultPlanId: string;
}) {
  const [title, setTitle] = React.useState("Tuition deposit");
  const [category, setCategory] = React.useState<PaymentCategory>("tuition");
  const [amount, setAmount] = React.useState("");
  const [currency, setCurrency] = React.useState(baseCurrency);
  const [dueDate, setDueDate] = React.useState("");
  const [status, setStatus] = React.useState<PaymentStatus>("planned");
  const [isRecurring, setIsRecurring] = React.useState(false);
  const [frequency, setFrequency] = React.useState<RecurrenceFrequency>("monthly");

  React.useEffect(() => setCurrency(baseCurrency), [baseCurrency]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Payment events</CardTitle>
        <p className="text-sm text-slate">
          Specific bills you expect to pay: deposits, tuition installments,
          rent, flights, visa fees. Recurring events (e.g. monthly rent)
          project forward into the timeline.
        </p>
      </CardHeader>
      <CardContent>
        {payments.length === 0 ? (
          <p className="text-sm text-slate">No payment events yet.</p>
        ) : (
          <ul className="mb-4 flex flex-col gap-2">
            {payments.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between rounded border border-border/60 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-midnight">{p.title}</span>
                  <span className="ml-2 text-slate">
                    {formatMoney(p.amount, p.currency)} · due {formatDate(p.due_date)} ·{" "}
                    <DisplayStatusBadge status={p.display_status} />
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(p.id)}
                  className="text-slate hover:text-red"
                  aria-label={`Remove ${p.title}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <form
          className="grid gap-3 sm:grid-cols-6"
          onSubmit={async (e) => {
            e.preventDefault();
            await onAdd({
              title,
              category,
              amount,
              currency: currency.toUpperCase(),
              due_date: dueDate,
              status,
              is_recurring: isRecurring,
              recurrence_frequency: isRecurring ? frequency : null,
              plan_id: defaultPlanId,
            });
            setAmount("");
            setDueDate("");
          }}
        >
          <Field label="Title" htmlFor="pe-title" required>
            <Input id="pe-title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <Field label="Category" htmlFor="pe-cat">
            <select
              id="pe-cat"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={category}
              onChange={(e) => setCategory(e.target.value as PaymentCategory)}
            >
              {PAYMENT_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Amount" htmlFor="pe-amt" required>
            <Input
              id="pe-amt"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
            />
          </Field>
          <Field label="Currency" htmlFor="pe-ccy" required>
            <Input
              id="pe-ccy"
              maxLength={3}
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Due date" htmlFor="pe-due" required>
            <Input
              id="pe-due"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </Field>
          <Field label="Status" htmlFor="pe-status">
            <select
              id="pe-status"
              className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value as PaymentStatus)}
            >
              {PAYMENT_STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
          <label className="col-span-full flex items-center gap-2 text-sm text-slate">
            <input
              type="checkbox"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
            />
            Recurring
          </label>
          {isRecurring ? (
            <Field label="Frequency" htmlFor="pe-freq">
              <select
                id="pe-freq"
                className="h-10 w-full rounded-lg border border-border bg-white px-2 text-sm"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as RecurrenceFrequency)}
              >
                {RECURRENCE_FREQUENCIES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </Field>
          ) : null}
          <div className="col-span-full flex justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              <Plus className="h-4 w-4" /> Add payment
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function DisplayStatusBadge({ status }: { status: PaymentEvent["display_status"] }) {
  const style: Record<PaymentEvent["display_status"], string> = {
    planned: "bg-ivory text-slate",
    scheduled: "bg-mint text-midnight",
    paid: "bg-teal text-white",
    overdue: "bg-red text-white",
    cancelled: "bg-slate-200 text-slate",
  };
  return (
    <span
      className={`ml-1 inline-block rounded px-1.5 py-0.5 text-xs ${style[status]}`}
    >
      {status}
    </span>
  );
}

function ConverterCard({ planId }: { planId: string }) {
  const [amount, setAmount] = React.useState("1000");
  const [fromCcy, setFromCcy] = React.useState("USD");
  const [toCcy, setToCcy] = React.useState("EUR");
  const [result, setResult] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Currency conversion preview</CardTitle>
        <p className="text-sm text-slate">
          Uses your saved FX rates. Add or update rates on the{" "}
          <a className="text-teal underline" href="/readiness">Readiness</a> page.
        </p>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-3 sm:grid-cols-5"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setErr(null);
            setResult(null);
            try {
              const r = await fundingPlanApi.convert(planId, {
                from_amount: amount,
                from_currency: fromCcy.toUpperCase(),
                to_currency: toCcy.toUpperCase(),
                fee_pct: null,
              });
              setResult(
                `${formatMoney(r.from_amount, r.from_currency)} → ${formatMoney(
                  r.total_cost,
                  r.to_currency,
                )} (incl. ${formatMoney(r.fee_amount, r.to_currency)} fee @ 1%)`,
              );
            } catch (caught) {
              setErr(errorMessage(caught, "Could not preview conversion."));
            } finally {
              setBusy(false);
            }
          }}
        >
          <Field label="Amount" htmlFor="cv-amt" required>
            <Input
              id="cv-amt"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </Field>
          <Field label="From" htmlFor="cv-from" required>
            <Input
              id="cv-from"
              maxLength={3}
              value={fromCcy}
              onChange={(e) => setFromCcy(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="To" htmlFor="cv-to" required>
            <Input
              id="cv-to"
              maxLength={3}
              value={toCcy}
              onChange={(e) => setToCcy(e.target.value.toUpperCase())}
            />
          </Field>
          <div className="flex items-end justify-end">
            <Button type="submit" size="sm" isLoading={busy}>
              Preview
            </Button>
          </div>
          {result || err ? (
            <p
              role={err ? "alert" : "status"}
              className={
                "col-span-full text-sm " + (err ? "text-red" : "text-midnight")
              }
            >
              {err ?? result}
            </p>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}

// studyPlansApi is referenced indirectly via the plan picker; we keep the
// import so the bundler doesn't drop it if a future change re-uses it.
void studyPlansApi;
