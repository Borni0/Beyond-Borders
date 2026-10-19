"use client";

/**
 * Financial Timeline workspace.
 *
 * A chronological view of every payment event the student owns (recurring
 * occurrences projected forward). At a glance the student sees what's due
 * next, what's overdue, and what can be marked paid or cancelled.
 */

import * as React from "react";
import { AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { paymentsApi } from "@/lib/payments-api";
import { fundingPlanApi } from "@/lib/payments-api";
import { ApiClientError } from "@/lib/client-api";
import { formatDate, formatMoney } from "@/lib/format";

import type {
  PaymentEvent,
  PaymentStatus,
  StudyPlan,
  TimelineEntry,
} from "@beyond-borders/shared-types";

interface Props {
  initialPlans: StudyPlan[];
  initialPlanId: string | null;
}

const STATUS_FILTERS: ReadonlyArray<PaymentEvent["display_status"] | "all"> = [
  "all", "overdue", "planned", "scheduled", "paid", "cancelled",
];

const STORED_STATUSES: PaymentStatus[] = [
  "planned", "scheduled", "paid", "cancelled",
];

export function TimelineWorkspace({ initialPlans, initialPlanId }: Props) {
  const [plans] = React.useState<StudyPlan[]>(initialPlans);
  const [activePlanId, setActivePlanId] = React.useState<string | null>(
    initialPlanId,
  );
  const [entries, setEntries] = React.useState<TimelineEntry[]>([]);
  const [owned, setOwned] = React.useState<PaymentEvent[]>([]);
  const [filter, setFilter] = React.useState<typeof STATUS_FILTERS[number]>(
    "all",
  );
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = React.useCallback(async (planId: string) => {
    setError(null);
    try {
      const [tl, own] = await Promise.all([
        fundingPlanApi.timeline(planId),
        paymentsApi.list({ plan_id: planId }),
      ]);
      setEntries(tl.entries);
      setOwned(own);
    } catch (err) {
      setError(errorMessage(err, "Could not load timeline."));
    }
  }, []);

  React.useEffect(() => {
    if (activePlanId) {
      void refresh(activePlanId);
    } else {
      setEntries([]);
      setOwned([]);
    }
  }, [activePlanId, refresh]);

  const updateStatus = async (eventId: string, status: PaymentStatus) => {
    setBusy(true);
    try {
      await paymentsApi.update(eventId, { status });
      if (activePlanId) await refresh(activePlanId);
    } catch (err) {
      setError(errorMessage(err, "Could not update status."));
    } finally {
      setBusy(false);
    }
  };

  const filtered = React.useMemo(() => {
    if (filter === "all") return entries;
    return entries.filter((e) => e.display_status === filter);
  }, [entries, filter]);

  const grouped = React.useMemo(() => groupByMonth(filtered), [filtered]);

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

      <Card>
        <CardHeader>
          <CardTitle>Plans</CardTitle>
        </CardHeader>
        <CardContent>
          {plans.length === 0 ? (
            <p className="text-sm text-slate">No plans yet.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {plans.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => setActivePlanId(p.id)}
                    className={
                      "rounded-lg border px-3 py-1.5 text-sm transition-colors " +
                      (p.id === activePlanId
                        ? "border-teal bg-mint/40 text-midnight"
                        : "border-border bg-white text-slate hover:bg-ivory")
                    }
                  >
                    {p.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {activePlanId ? (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>Upcoming payments</CardTitle>
              <FilterPicker value={filter} onChange={setFilter} />
            </div>
          </CardHeader>
          <CardContent>
            {filtered.length === 0 ? (
              <p className="text-sm text-slate">
                Nothing matches this filter.
              </p>
            ) : (
              <ol className="flex flex-col gap-6">
                {grouped.map((group) => (
                  <li key={group.label}>
                    <h3 className="mb-2 text-sm font-medium text-slate">
                      {group.label}
                    </h3>
                    <ul className="flex flex-col gap-2">
                      {group.entries.map((entry) => (
                        <li
                          key={`${entry.event_id}-${entry.due_date}`}
                          className="flex flex-wrap items-center justify-between gap-3 rounded border border-border/60 px-3 py-2 text-sm"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-midnight">
                                {entry.title}
                              </span>
                              <StatusBadge status={entry.display_status} />
                              {entry.is_recurring ? (
                                <span className="rounded bg-ivory px-1.5 py-0.5 text-xs text-slate">
                                  recurring
                                </span>
                              ) : null}
                            </div>
                            <p className="mt-0.5 text-xs text-slate">
                              {entry.category} · {formatDate(entry.due_date)}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="tabular-nums text-midnight">
                              {formatMoney(entry.amount, entry.currency)}
                            </span>
                            <StatusActions
                              eventId={entry.event_id}
                              onSetStatus={updateStatus}
                              busy={busy}
                            />
                          </div>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>
      ) : null}

      {activePlanId && owned.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>All payment events</CardTitle>
            <p className="text-sm text-slate">
              Edit stored status or remove an event. Recurring events are
              stored once; the timeline above projects them forward.
            </p>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-2">
              {owned.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded border border-border/60 px-3 py-2 text-sm"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-midnight">
                        {p.title}
                      </span>
                      <StatusBadge status={p.display_status} />
                    </div>
                    <p className="mt-0.5 text-xs text-slate">
                      {p.category} · {formatDate(p.due_date)} ·{" "}
                      {p.is_recurring
                        ? `recurring (${p.recurrence_frequency})`
                        : "one-time"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="tabular-nums">
                      {formatMoney(p.amount, p.currency)}
                    </span>
                    <select
                      aria-label={`Status of ${p.title}`}
                      className="h-8 rounded border border-border bg-white px-2 text-xs"
                      value={
                        p.display_status === "overdue" ? "planned" : p.display_status
                      }
                      onChange={(e) =>
                        updateStatus(p.id, e.target.value as PaymentStatus)
                      }
                      disabled={busy}
                    >
                      {STORED_STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message ?? fallback;
  if (err instanceof Error) return err.message;
  return fallback;
}

function FilterPicker({
  value,
  onChange,
}: {
  value: typeof STATUS_FILTERS[number];
  onChange: (v: typeof STATUS_FILTERS[number]) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 text-xs">
      {STATUS_FILTERS.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className={
            "rounded-full px-2.5 py-1 transition-colors " +
            (value === s
              ? "bg-teal text-white"
              : "bg-ivory text-slate hover:bg-mint")
          }
        >
          {s}
        </button>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: PaymentEvent["display_status"] }) {
  const style: Record<PaymentEvent["display_status"], string> = {
    planned: "bg-ivory text-slate",
    scheduled: "bg-mint text-midnight",
    paid: "bg-teal text-white",
    overdue: "bg-red text-white",
    cancelled: "bg-slate-200 text-slate",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs ${style[status]}`}>
      {status}
    </span>
  );
}

function StatusActions({
  eventId,
  onSetStatus,
  busy,
}: {
  eventId: string;
  onSetStatus: (id: string, status: PaymentStatus) => Promise<void>;
  busy: boolean;
}) {
  return (
    <div className="flex gap-1">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onSetStatus(eventId, "paid")}
        isLoading={busy}
        aria-label="Mark paid"
      >
        Paid
      </Button>
      <Button
        size="sm"
        variant="secondary"
        onClick={() => onSetStatus(eventId, "cancelled")}
        isLoading={busy}
        aria-label="Cancel"
      >
        Cancel
      </Button>
    </div>
  );
}

function groupByMonth(
  entries: TimelineEntry[],
): { label: string; entries: TimelineEntry[] }[] {
  const out = new Map<string, TimelineEntry[]>();
  for (const e of entries) {
    const d = new Date(e.due_date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const list = out.get(key) ?? [];
    list.push(e);
    out.set(key, list);
  }
  return Array.from(out.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, list]) => ({
      label: formatMonthLabel(key),
      entries: list,
    }));
}

function formatMonthLabel(yyyymm: string): string {
  const [y, m] = yyyymm.split("-").map(Number);
  const date = new Date(y ?? 0, (m ?? 1) - 1, 1);
  return date.toLocaleString("en-US", { month: "long", year: "numeric" });
}