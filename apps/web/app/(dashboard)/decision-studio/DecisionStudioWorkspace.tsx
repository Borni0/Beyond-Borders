"use client";

/**
 * Decision Studio workspace.
 *
 * Lets the user pick 2 or 3 study plans, see a side-by-side comparison
 * of cost / funding / upfront cash / payments, optionally apply
 * per-plan scenarios, and save / reopen / rename / delete comparisons.
 *
 * Numeric math is done on the backend; this component is pure
 * orchestration + presentation.
 */

import * as React from "react";
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronRight,
  Pencil,
  Plus,
  Save,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";
import { decisionStudioApi } from "@/lib/decision-studio-api";
import { ApiClientError } from "@/lib/client-api";
import { formatDate, formatMoney } from "@/lib/format";

import type {
  CompareRequest,
  CompareResult,
  ComparisonRow,
  ComparisonWarning,
  SavedComparisonCreate,
  SavedComparisonPublic,
  ScenarioAdjustment,
  ScenarioAdjustmentType,
  ScenarioSpec,
  StudyPlan,
} from "@beyond-borders/shared-types";

const ADJUSTMENT_TYPES: { value: ScenarioAdjustmentType; label: string; expectsValue: boolean }[] = [
  { value: "rent_increase_pct", label: "Rent increase (%)", expectsValue: true },
  { value: "tuition_increase_pct", label: "Tuition increase (%)", expectsValue: true },
  { value: "scholarship_reduction_pct", label: "Scholarship reduction (%)", expectsValue: true },
  { value: "family_support_delay_days", label: "Family support delay (days)", expectsValue: true },
  { value: "fx_shift_pct", label: "FX shift (%)", expectsValue: true },
  { value: "deposit_change", label: "Deposit change (signed)", expectsValue: true },
  { value: "custom_note", label: "Custom note (no value)", expectsValue: false },
];

const COMPLETENESS_TONE: Record<string, string> = {
  complete: "bg-teal/10 text-teal-dark border-teal/30",
  partial: "bg-amber/10 text-amber border-amber/30",
  missing: "bg-red/10 text-red border-red/30",
};

const COMPLETENESS_LABEL: Record<string, string> = {
  complete: "Complete data",
  partial: "Partial data",
  missing: "Missing data",
};

const WARNING_TONE: Record<string, string> = {
  missing_costs: "border-amber/30 bg-amber/5 text-amber",
  missing_funding: "border-amber/30 bg-amber/5 text-amber",
  missing_fx: "border-amber/30 bg-amber/5 text-amber",
  different_currencies: "border-slate/30 bg-slate/5 text-slate",
  different_durations: "border-slate/30 bg-slate/5 text-slate",
  incomplete_data: "border-amber/30 bg-amber/5 text-amber",
  no_known_payments: "border-slate/30 bg-slate/5 text-slate",
};

interface Props {
  initialPlans: StudyPlan[];
}

function parseDecimal(value: string | undefined | null): number {
  if (value === undefined || value === null || value === "") return 0;
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function DecisionStudioWorkspace({ initialPlans }: Props) {
  const [plans] = React.useState<StudyPlan[]>(initialPlans);
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [scenarios, setScenarios] = React.useState<ScenarioSpec[]>([]);
  const [upfrontWindow, setUpfrontWindow] = React.useState(30);
  const [result, setResult] = React.useState<CompareResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [saved, setSaved] = React.useState<SavedComparisonPublic[]>([]);
  const [renamingId, setRenamingId] = React.useState<string | null>(null);
  const [renameValue, setRenameValue] = React.useState("");

  // ---- helpers ---------------------------------------------------------

  const refreshSaved = React.useCallback(async () => {
    try {
      const list = await decisionStudioApi.listSaved();
      setSaved(list);
    } catch (err) {
      setError(messageOf(err, "Could not load saved comparisons."));
    }
  }, []);

  React.useEffect(() => {
    void refreshSaved();
  }, [refreshSaved]);

  // Default selection: pick the first two plans the user has.
  React.useEffect(() => {
    if (selectedIds.length === 0 && plans.length >= 2) {
      setSelectedIds([plans[0]!.id, plans[1]!.id]);
    }
  }, [plans, selectedIds.length]);

  const togglePlan = (id: string) => {
    setSelectedIds((cur) => {
      if (cur.includes(id)) return cur.filter((p) => p !== id);
      if (cur.length >= 3) return [...cur.slice(1), id];
      return [...cur, id];
    });
  };

  const buildCompareRequest = (): CompareRequest | null => {
    if (selectedIds.length < 2 || selectedIds.length > 3) return null;
    const req: CompareRequest = {
      study_plan_ids: [...selectedIds],
      upfront_window_days: upfrontWindow,
    };
    const activeScenarios = scenarios.filter((s) => selectedIds.includes(s.plan_id));
    if (activeScenarios.length > 0) req.scenarios = activeScenarios;
    return req;
  };

  const runCompare = async () => {
    setError(null);
    const req = buildCompareRequest();
    if (!req) {
      setError("Pick 2 or 3 plans to compare.");
      return;
    }
    setBusy(true);
    try {
      const r = await decisionStudioApi.compare(req);
      setResult(r);
    } catch (err) {
      setResult(null);
      setError(messageOf(err, "Comparison failed."));
    } finally {
      setBusy(false);
    }
  };

  const addAdjustment = (planId: string, type: ScenarioAdjustmentType) => {
    setScenarios((cur) => upsertScenarioAdjustment(cur, planId, type));
  };

  const removeAdjustment = (planId: string, idx: number) => {
    setScenarios((cur) => removeScenarioAdjustmentAt(cur, planId, idx));
  };

  const updateAdjustment = (
    planId: string,
    idx: number,
    patch: Partial<ScenarioAdjustment>,
  ) => {
    setScenarios((cur) => patchScenarioAdjustment(cur, planId, idx, patch));
  };

  const saveCurrent = async () => {
    setError(null);
    if (!result || selectedIds.length < 2) {
      setError("Run a comparison before saving.");
      return;
    }
    const name = window.prompt("Name this comparison:", `Comparison ${new Date().toLocaleDateString()}`);
    if (!name) return;
    const payload: SavedComparisonCreate = {
      name,
      study_plan_ids: [...selectedIds],
    };
    if (scenarios.filter((s) => selectedIds.includes(s.plan_id)).length > 0) {
      payload.scenarios = scenarios.filter((s) =>
        selectedIds.includes(s.plan_id),
      );
    }
    setBusy(true);
    try {
      await decisionStudioApi.createSaved(payload);
      await refreshSaved();
    } catch (err) {
      setError(messageOf(err, "Could not save comparison."));
    } finally {
      setBusy(false);
    }
  };

  const openSaved = async (id: string) => {
    setError(null);
    setBusy(true);
    try {
      const detail = await decisionStudioApi.openSaved(id);
      setSelectedIds(detail.comparison.study_plan_ids);
      setScenarios(detail.comparison.scenarios ?? []);
      setResult(detail.result);
    } catch (err) {
      setError(messageOf(err, "Could not open comparison."));
    } finally {
      setBusy(false);
    }
  };

  const deleteSaved = async (id: string) => {
    if (!window.confirm("Delete this saved comparison? This cannot be undone.")) return;
    setBusy(true);
    try {
      await decisionStudioApi.removeSaved(id);
      await refreshSaved();
    } catch (err) {
      setError(messageOf(err, "Could not delete comparison."));
    } finally {
      setBusy(false);
    }
  };

  const submitRename = async (id: string) => {
    const name = renameValue.trim();
    if (!name) {
      setRenamingId(null);
      return;
    }
    setBusy(true);
    try {
      await decisionStudioApi.updateSaved(id, { name });
      setRenamingId(null);
      await refreshSaved();
    } catch (err) {
      setError(messageOf(err, "Could not rename."));
    } finally {
      setBusy(false);
    }
  };

  // ---- render ----------------------------------------------------------

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">Decision Studio</h1>
        <p className="text-sm text-slate">
          Compare up to three study-abroad plans side by side. All numbers are
          re-computed from the underlying plans whenever you re-run a comparison.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Pick 2 or 3 plans</CardTitle>
          <CardDescription>
            Selections are local to your browser until you click
            <span className="mx-1 rounded bg-ivory px-1.5 py-0.5 font-mono text-xs">Compare</span>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {plans.length === 0 ? (
            <p className="text-sm text-slate">
              You have no study plans yet. Create at least two on the
              <a href="/study-plans" className="ml-1 underline">Study Plans</a> page.
            </p>
          ) : (
            <ul className="grid gap-2 md:grid-cols-2">
              {plans.map((p) => {
                const checked = selectedIds.includes(p.id);
                return (
                  <li key={p.id}>
                    <label className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 transition-colors ${checked ? "border-teal bg-teal/5" : "border-border bg-white hover:border-teal/40"}`}>
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={checked}
                        onChange={() => togglePlan(p.id)}
                      />
                      <span className="flex flex-col text-sm">
                        <span className="font-medium text-midnight">{p.name}</span>
                        <span className="text-xs text-slate">
                          {p.destination_country ?? "—"} ·{" "}
                          {formatDate(p.start_date)} · {p.duration_months} mo ·{" "}
                          {p.base_currency}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compare</CardTitle>
          <CardDescription>
            Results are never cached. The backend re-runs the readiness engine
            for every selected plan.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <Field
              label="Upfront window (days)"
              htmlFor="ds-upfront"
            >
              <Input
                id="ds-upfront"
                type="number"
                min={1}
                max={365}
                value={String(upfrontWindow)}
                onChange={(e) => setUpfrontWindow(Number(e.target.value) || 30)}
                className="w-32"
              />
            </Field>
            <Button
              type="button"
              onClick={() => void runCompare()}
              disabled={busy || selectedIds.length < 2 || selectedIds.length > 3}
            >
              {busy ? "Comparing…" : "Compare"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void saveCurrent()}
              disabled={busy || !result}
            >
              <Save className="mr-1 h-4 w-4" />
              Save comparison
            </Button>
            <p className="ml-auto text-xs text-slate">
              {selectedIds.length} of 3 plans selected
            </p>
          </div>
          {error ? (
            <div className="mt-3 flex items-start gap-2 rounded-md border border-red/30 bg-red/5 px-3 py-2 text-sm text-red">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {result ? (
        <>
          <DeadlineRankingCard result={result} />
          <ComparisonView result={result} />
        </>
      ) : null}

      {selectedIds.length > 0 ? (
        <ScenariosEditor
          plans={plans.filter((p) => selectedIds.includes(p.id))}
          scenarios={scenarios}
          onAdd={addAdjustment}
          onRemove={removeAdjustment}
          onUpdate={updateAdjustment}
        />
      ) : null}

      <SavedComparisonsPanel
        items={saved}
        renamingId={renamingId}
        renameValue={renameValue}
        setRenameValue={setRenameValue}
        setRenamingId={setRenamingId}
        onOpen={(id) => void openSaved(id)}
        onDelete={(id) => void deleteSaved(id)}
        onSubmitRename={(id) => void submitRename(id)}
      />
    </div>
  );
}

// ---------- Comparison view -----------------------------------------------

function DeadlineRankingCard({ result }: { result: CompareResult }) {
  const rankings = result.deadline_rankings?.length ? result.deadline_rankings : computeDeadlineRankings(result.plans);
  if (!rankings.length) return null;

  const winner = rankings[0] ?? null;
  if (!winner) return null;

  const winnerRow = result.plans.find((row) => row.plan.id === winner.plan_id) ?? result.plans[0] ?? null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deadline-aware ranking</CardTitle>
        <CardDescription>
          Recommended plan: {winnerRow ? winnerRow.plan.name : "—"} · {winner.status === "no_shortfall" ? "cash-positive by deadline" : "earliest shortfall noted"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-3 rounded-lg border border-teal/30 bg-teal/5 p-3 text-sm text-midnight">
          <div className="font-medium">{winnerRow?.plan.name ?? "Winner"}</div>
          <div className="mt-1 text-slate">
            {winner.rationale}
          </div>
        </div>
        <ol className="grid gap-2 md:grid-cols-3">
          {rankings.map((r) => {
            const plan = result.plans.find((row) => row.plan.id === r.plan_id);
            return (
              <li key={r.plan_id} className="rounded-lg border border-border bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-midnight">#{r.rank} {plan?.plan.name ?? "Plan"}</span>
                  <span className="rounded-full bg-ivory px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate">
                    {r.status.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate">
                  {r.earliest_shortfall_date ? (
                    <span>
                      Earliest shortfall: {formatDate(r.earliest_shortfall_date)}
                    </span>
                  ) : (
                    <span>No cash shortfall detected</span>
                  )}
                </div>
                {r.shortfall_amount ? (
                  <div className="mt-1 text-xs text-red">
                    Shortfall: {formatMoney(r.shortfall_amount, plan?.cost.base_currency ?? "USD")}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}

function ComparisonView({ result }: { result: CompareResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Side-by-side</CardTitle>
        <CardDescription>
          {result.plans.length} plans · engine{" "}
          <span className="font-mono text-xs">{result.calculation_version}</span>{" "}
          · generated {new Date(result.generated_at).toLocaleString()}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {result.warnings.length > 0 ? (
          <ul className="mb-4 grid gap-2 md:grid-cols-2">
            {result.warnings.map((w, i) => (
              <li
                key={`${w.code}-${i}`}
                className={`rounded-md border px-3 py-2 text-xs ${WARNING_TONE[w.code] ?? "border-slate/30 bg-slate/5 text-slate"}`}
              >
                <span className="font-medium">{w.code.replace(/_/g, " ")}</span>
                <span className="ml-2 text-slate">{w.message}</span>
              </li>
            ))}
          </ul>
        ) : null}

        <div className={`grid gap-4 ${result.plans.length === 2 ? "md:grid-cols-2" : "md:grid-cols-3"}`}>
          {result.plans.map((row) => (
            <PlanColumn key={row.plan.id} row={row} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function PlanColumn({ row }: { row: ComparisonRow }) {
  const { plan, cost, funding, upfront, earliest_payment, payments } = row;
  const [showAllPayments, setShowAllPayments] = React.useState(false);
  const gap = parseDecimal(funding.funding_gap);
  const surplus = parseDecimal(funding.funding_surplus);
  const upfrontGap = parseDecimal(upfront.upfront_cash_gap);
  const visiblePayments = showAllPayments ? payments : payments.slice(0, 5);

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-ivory/50 p-4">
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-base font-semibold text-midnight">
            {plan.name}
            {plan.scenario_name !== "baseline" ? (
              <span className="ml-2 rounded bg-mint/40 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-teal-dark">
                {plan.scenario_name}
              </span>
            ) : null}
          </h3>
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${COMPLETENESS_TONE[plan.data_completeness] ?? "border-border text-slate"}`}
            title={plan.missing_inputs.join(" · ")}
          >
            {COMPLETENESS_LABEL[plan.data_completeness] ?? plan.data_completeness}
          </span>
        </div>
        <p className="text-xs text-slate">
          {plan.institution_name ?? plan.destination_country ?? "—"} ·{" "}
          {plan.city ?? "—"} · {formatDate(plan.start_date)} → {formatDate(plan.end_date)} ({plan.duration_months} mo)
        </p>
      </div>

      <Section title="Cost">
        <Row label={`Total (${cost.displayed_period_months} mo)`} value={formatMoney(cost.cost_for_displayed_period, cost.base_currency)} />
        <Row label="First year" value={formatMoney(cost.first_year_cost, cost.base_currency)} />
        <Row label="Refundable deposits" value={formatMoney(cost.refundable_deposits, cost.base_currency)} />
      </Section>

      <Section title="Funding">
        <Row label="Confirmed" value={formatMoney(funding.confirmed_total, funding.base_currency)} />
        <Row label="Expected / conditional" value={formatMoney(
          parseDecimal(funding.conditional_total) + parseDecimal(funding.expected_total),
          funding.base_currency,
        )} />
        <Row
          label="Eligible (confirmed)"
          value={formatMoney(funding.eligible_confirmed, funding.base_currency)}
        />
        {gap > 0 ? (
          <Row label="Funding gap" value={formatMoney(funding.funding_gap, funding.base_currency)} tone="danger" />
        ) : (
          <Row label="Funding surplus" value={formatMoney(funding.funding_surplus, funding.base_currency)} tone="ok" />
        )}
      </Section>

      <Section title={`Upfront (${upfront.upfront_window_days} days)`}>
        <Row label="Cash required" value={formatMoney(upfront.upfront_cash_requirement, upfront.base_currency)} />
        <Row
          label="Cash gap"
          value={formatMoney(upfront.upfront_cash_gap, upfront.base_currency)}
          tone={upfrontGap > 0 ? "danger" : "ok"}
        />
      </Section>

      <Section title="Earliest payment">
        {earliest_payment ? (
          <div className="flex flex-col gap-0.5 text-xs">
            <span className="font-medium text-midnight">
              {earliest_payment.title}
            </span>
            <span className="text-slate">
              {formatMoney(earliest_payment.amount, earliest_payment.currency)} ·{" "}
              {earliest_payment.due_date ? formatDate(earliest_payment.due_date) : "no due date"} ·{" "}
              <span className="rounded bg-ivory px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                {earliest_payment.display_status}
              </span>
            </span>
          </div>
        ) : (
          <span className="text-xs text-slate">No payment events recorded.</span>
        )}
      </Section>

      <Section title={`Payments (${payments.length})`}>
        {payments.length === 0 ? (
          <span className="text-xs text-slate">None.</span>
        ) : (
          <>
            <ul className="flex flex-col gap-1">
              {visiblePayments.map((p) => (
                <li key={p.id} className="flex items-center justify-between text-xs">
                  <span className="truncate text-midnight">
                    {p.title}{" "}
                    <span className="rounded bg-ivory px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate">
                      {p.display_status}
                    </span>
                  </span>
                  <span className="ml-2 text-slate">
                    {formatMoney(p.amount, p.currency)}
                    {p.due_date ? <> · {formatDate(p.due_date)}</> : null}
                  </span>
                </li>
              ))}
            </ul>
            {payments.length > 5 ? (
              <button
                type="button"
                onClick={() => setShowAllPayments((v) => !v)}
                className="mt-1 self-start text-xs text-teal-dark underline"
              >
                {showAllPayments ? "Show fewer" : `Show all (${payments.length})`}
              </button>
            ) : null}
          </>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate">{title}</h4>
      <div className="flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "ok" | "danger";
}) {
  const toneClass =
    tone === "ok" ? "text-teal-dark" : tone === "danger" ? "text-red" : "text-midnight";
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate">{label}</span>
      <span className={`tabular-nums font-medium ${toneClass}`}>{value}</span>
    </div>
  );
}

// ---------- Scenarios editor ---------------------------------------------

function ScenariosEditor({
  plans,
  scenarios,
  onAdd,
  onRemove,
  onUpdate,
}: {
  plans: StudyPlan[];
  scenarios: ScenarioSpec[];
  onAdd: (planId: string, type: ScenarioAdjustmentType) => void;
  onRemove: (planId: string, idx: number) => void;
  onUpdate: (planId: string, idx: number, patch: Partial<ScenarioAdjustment>) => void;
}) {
  const [openPlan, setOpenPlan] = React.useState<string | null>(null);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scenarios (what-if)</CardTitle>
        <CardDescription>
          Adjustments apply to in-memory copies of the plan — your saved
          plans are never changed. Re-run Compare to see the new numbers.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-3">
          {plans.map((p) => {
            const sc = scenarios.find((s) => s.plan_id === p.id) ?? {
              plan_id: p.id,
              name: "baseline",
              adjustments: [],
            };
            const expanded = openPlan === p.id;
            return (
              <li key={p.id} className="rounded-lg border border-border bg-white p-3">
                <button
                  type="button"
                  onClick={() => setOpenPlan(expanded ? null : p.id)}
                  className="flex w-full items-center justify-between text-sm font-medium text-midnight"
                >
                  <span className="flex items-center gap-2">
                    {expanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    {p.name}{" "}
                    <span className="text-xs font-normal text-slate">
                      ({sc.name === "baseline" ? "no scenario" : sc.name})
                    </span>
                  </span>
                  <span className="text-xs text-slate">
                    {sc.adjustments.length} adjustment{sc.adjustments.length === 1 ? "" : "s"}
                  </span>
                </button>
                {expanded ? (
                  <div className="mt-3 flex flex-col gap-3 pl-6 text-sm">
                    <Field label="Scenario name" htmlFor={`sc-name-${p.id}`}>
                      <Input
                        id={`sc-name-${p.id}`}
                        value={sc.name === "baseline" ? "" : sc.name}
                        placeholder="baseline"
                        onChange={(e) =>
                          onUpdate(p.id, 0, { type: "custom_note", note: e.target.value })
                        }
                      />
                    </Field>
                    {sc.adjustments.length > 0 ? (
                      <ul className="flex flex-col gap-2">
                        {sc.adjustments.map((adj, i) => (
                          <li
                            key={i}
                            className="flex flex-wrap items-end gap-2 rounded border border-border bg-ivory/40 p-2"
                          >
                            <span className="text-xs text-slate">
                              {ADJUSTMENT_TYPES.find((t) => t.value === adj.type)?.label ?? adj.type}
                            </span>
                            <Input
                              className="w-32"
                              value={adj.value ?? ""}
                              placeholder="value"
                              onChange={(e) => onUpdate(p.id, i, { value: e.target.value })}
                            />
                            <Input
                              className="flex-1 min-w-[8rem]"
                              value={adj.note ?? ""}
                              placeholder="note (optional)"
                              onChange={(e) => onUpdate(p.id, i, { note: e.target.value })}
                            />
                            <Button
                              type="button"
                              variant="ghost"
                              onClick={() => onRemove(p.id, i)}
                              aria-label="Remove adjustment"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    <div className="flex flex-wrap items-center gap-2">
                      {ADJUSTMENT_TYPES.map((t) => (
                        <Button
                          key={t.value}
                          type="button"
                          variant="secondary"
                          onClick={() => onAdd(p.id, t.value)}
                        >
                          <Plus className="mr-1 h-4 w-4" />
                          {t.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

// ---------- Saved comparisons panel --------------------------------------

function SavedComparisonsPanel({
  items,
  renamingId,
  renameValue,
  setRenameValue,
  setRenamingId,
  onOpen,
  onDelete,
  onSubmitRename,
}: {
  items: SavedComparisonPublic[];
  renamingId: string | null;
  renameValue: string;
  setRenameValue: (v: string) => void;
  setRenamingId: (id: string | null) => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onSubmitRename: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Saved comparisons</CardTitle>
        <CardDescription>
          Reopening a saved comparison re-computes every number from the
          underlying plans.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-2">
          {items.map((c) => (
            <li
              key={c.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-white p-3"
            >
              <div className="flex flex-col text-sm">
                {renamingId === c.id ? (
                  <Input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") onSubmitRename(c.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    onBlur={() => onSubmitRename(c.id)}
                  />
                ) : (
                  <span className="font-medium text-midnight">{c.name}</span>
                )}
                <span className="text-xs text-slate">
                  {c.study_plan_ids.length} plans · engine {c.calculation_version} ·{" "}
                  updated {formatDate(c.updated_at)}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Button type="button" variant="secondary" onClick={() => onOpen(c.id)}>
                  Open
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setRenamingId(c.id);
                    setRenameValue(c.name);
                  }}
                  aria-label="Rename"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onDelete(c.id)}
                  aria-label="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
                <Check className="hidden" />
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// ---------- Pure helpers -------------------------------------------------

function upsertScenarioAdjustment(
  cur: ScenarioSpec[],
  planId: string,
  type: ScenarioAdjustmentType,
): ScenarioSpec[] {
  const adj: ScenarioAdjustment = { type, value: "", note: null };
  return cur.map((s) =>
    s.plan_id === planId
      ? { ...s, name: s.name === "baseline" ? "what-if" : s.name, adjustments: [...s.adjustments, adj] }
      : s,
  );
}

function removeScenarioAdjustmentAt(
  cur: ScenarioSpec[],
  planId: string,
  idx: number,
): ScenarioSpec[] {
  return cur
    .map((s) =>
      s.plan_id === planId
        ? { ...s, adjustments: s.adjustments.filter((_, i) => i !== idx) }
        : s,
    )
    .filter((s) => s.adjustments.length > 0);
}

function patchScenarioAdjustment(
  cur: ScenarioSpec[],
  planId: string,
  idx: number,
  patch: Partial<ScenarioAdjustment>,
): ScenarioSpec[] {
  return cur.map((s) => {
    if (s.plan_id !== planId) return s;
    const next = s.adjustments.map((a, i) => (i === idx ? { ...a, ...patch } : a));
    return { ...s, adjustments: next };
  });
}

function computeDeadlineRankings(rows: ComparisonRow[]) {
  return rows
    .map((row) => {
      const payments = row.payments.filter((p) => p.due_date);
      if (payments.length === 0) {
        return {
          plan_id: row.plan.id,
          rank: 1,
          score: 0,
          status: "no_payment_data" as const,
          earliest_shortfall_date: null,
          shortfall_amount: null,
          rationale: "No payment deadlines were entered, so the plan cannot be ranked on cash timing yet.",
        };
      }

      const byDate = new Map<string, number>();
      for (const p of payments) {
        if (!p.due_date) continue;
        byDate.set(p.due_date, (byDate.get(p.due_date) ?? 0) + parseDecimal(p.amount));
      }

      const available = parseDecimal(row.funding.available_before_departure);
      const amounts = Array.from(byDate.entries()).sort(([a], [b]) => a.localeCompare(b));
      let cumulativeDue = 0;
      let cumulativeAvailable = available;
      let earliestShortfall: string | null = null;
      let shortfall = 0;

      for (const [, amt] of amounts) {
        cumulativeDue += amt;
        if (cumulativeAvailable < cumulativeDue) {
          earliestShortfall = amounts[0]?.[0] ?? null;
          shortfall = cumulativeDue - cumulativeAvailable;
          break;
        }
      }

      if (!earliestShortfall) {
        return {
          plan_id: row.plan.id,
          rank: 1,
          score: 100,
          status: "no_shortfall" as const,
          earliest_shortfall_date: null,
          shortfall_amount: null,
          rationale: "Confirmed and expected funding arrives before every known payment deadline.",
        };
      }

      return {
        plan_id: row.plan.id,
        rank: 1,
        score: Math.max(0, 100 - Math.round(shortfall / 1000)),
        status: "shortfall" as const,
        earliest_shortfall_date: earliestShortfall,
        shortfall_amount: String(shortfall),
        rationale: `Earliest cash shortfall appears on ${earliestShortfall}; the plan is ${shortfall} short on the critical deadline.`,
      };
    })
    .sort((a, b) => {
      if (a.status === b.status) return b.score - a.score;
      if (a.status === "no_shortfall") return -1;
      if (b.status === "no_shortfall") return 1;
      if (a.status === "shortfall") return -1;
      return 1;
    })
    .map((entry, index) => ({ ...entry, rank: index + 1 }));
}

function messageOf(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}
