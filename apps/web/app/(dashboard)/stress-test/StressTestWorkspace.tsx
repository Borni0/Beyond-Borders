/**
 * Stress Test (Financial Weather) workspace.
 *
 * Three building blocks:
 *
 *   1. Pick a plan.
 *   2. Pick a preset (or build a custom one) and adjust the value.
 *   3. Run the scenario — the readiness engine re-runs against a
 *      scenario-applied copy of the plan, and the page shows
 *      baseline-vs-scenario deltas side by side.
 *
 * Saved scenarios persist so the user can re-run the same shock
 * against any plan later.
 */

"use client";

import * as React from "react";

import type {
  StressRunResult,
  StressScenario,
  StressScenarioKey,
  StudyPlan,
} from "@beyond-borders/shared-types";

import { ApiClientError } from "@/lib/client-api";
import { stressTestApi, type StressPresetMap } from "@/lib/stress-test-api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatMoney } from "@/lib/format";

const DEFAULT_PRESET: StressScenarioKey = "rent_shock";

function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}

function adjustmentValueFor(key: StressScenarioKey, preset: StressPresetMap | null): string {
  if (!preset) return "";
  const adj = preset[key].default_adjustment;
  if (adj.value !== null && adj.value !== undefined) return adj.value;
  return "";
}

function adjustmentToText(key: StressScenarioKey, value: string, note: string): string {
  switch (key) {
    case "rent_shock":
      return `+${value}% rent & utilities`;
    case "scholarship_cut":
      return `−${value}% scholarships`;
    case "tuition_shock":
      return `+${value}% tuition`;
    case "living_expense_shock":
      return `+${value}% living expenses`;
    case "fx_shock":
      return `FX −${value}% (informational)`;
    case "family_delay":
      return `Family +${value} days`;
    case "custom":
      return note.length > 0 ? note : "Custom scenario";
  }
}

export function StressTestWorkspace({ initialPlans }: { initialPlans: StudyPlan[] }) {
  const [plans, setPlans] = React.useState<StudyPlan[]>(initialPlans);
  const [planId, setPlanId] = React.useState<string>(initialPlans[0]?.id ?? "");
  const [presets, setPresets] = React.useState<StressPresetMap | null>(null);
  const [preset, setPreset] = React.useState<StressScenarioKey>(DEFAULT_PRESET);
  const [value, setValue] = React.useState<string>("25");
  const [note, setNote] = React.useState<string>("");
  const [scenarios, setScenarios] = React.useState<StressScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = React.useState<string>("");
  const [name, setName] = React.useState<string>("");
  const [result, setResult] = React.useState<StressRunResult | null>(null);
  const [loadingPresets, setLoadingPresets] = React.useState(true);
  const [loadingScenarios, setLoadingScenarios] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  // Load presets on mount.
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { presets: map } = await stressTestApi.presets();
        if (cancelled) return;
        setPresets(map);
        setValue(adjustmentValueFor(DEFAULT_PRESET, map));
      } catch (err) {
        setError(describeError(err, "Could not load stress-test presets."));
      } finally {
        if (!cancelled) setLoadingPresets(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // When preset changes, refresh the value to the preset's default.
  React.useEffect(() => {
    if (presets) setValue(adjustmentValueFor(preset, presets));
  }, [preset, presets]);

  // Load saved scenarios for the current plan.
  const reloadScenarios = React.useCallback(async (pid: string) => {
    setLoadingScenarios(true);
    try {
      const rows = await stressTestApi.listScenarios(pid);
      setScenarios(rows);
    } catch (err) {
      setError(describeError(err, "Could not load saved scenarios."));
    } finally {
      setLoadingScenarios(false);
    }
  }, []);

  React.useEffect(() => {
    if (planId) void reloadScenarios(planId);
    setSelectedScenario("");
  }, [planId, reloadScenarios]);

  async function handleRun() {
    if (!planId) {
      setError("Pick a plan first.");
      return;
    }
    setError(null);
    setSuccess(null);
    setRunning(true);
    try {
      let res: StressRunResult;
      if (selectedScenario) {
        const scenarioName = scenarios.find((scenario) => scenario.id === selectedScenario)?.name ?? "Saved scenario";
        res = await stressTestApi.run({
          plan_id: planId,
          scenario_id: selectedScenario,
          scenario_name: scenarioName,
          upfront_window_days: 30,
        });
      } else {
        const adjustment = buildAdjustment(preset, value, note);
        res = await stressTestApi.run({
          plan_id: planId,
          adjustments: [adjustment],
          scenario_name:
            preset === "custom" && note ? note : (presets?.[preset]?.label ?? preset),
          upfront_window_days: 30,
        });
      }
      setResult(res);
    } catch (err) {
      setError(describeError(err, "Could not run the scenario."));
    } finally {
      setRunning(false);
    }
  }

  async function handleSave() {
    if (!planId) {
      setError("Pick a plan first.");
      return;
    }
    if (name.trim().length === 0) {
      setError("Please name the scenario before saving.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const adjustment = buildAdjustment(preset, value, note);
      const created = await stressTestApi.createScenario({
        name: name.trim(),
        scenario_key: preset,
        adjustments: [adjustment],
        plan_id: planId,
        notes: note.trim() === "" ? null : note.trim(),
      });
      setSuccess(`Saved “${created.name}”.`);
      setName("");
      await reloadScenarios(planId);
    } catch (err) {
      setError(describeError(err, "Could not save the scenario."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(s: StressScenario) {
    if (!window.confirm(`Delete scenario “${s.name}”?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await stressTestApi.removeScenario(s.id);
      if (selectedScenario === s.id) setSelectedScenario("");
      setSuccess(`Deleted “${s.name}”.`);
      await reloadScenarios(planId);
    } catch (err) {
      setError(describeError(err, "Could not delete the scenario."));
    }
  }

  const hasPlans = plans.length > 0;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">Stress Test</h1>
        <p className="text-sm text-slate">
          Model the impact of an FX shock, rent increase, scholarship cut,
          or family-support delay on a single plan. The same engine that
          powers Financial Readiness re-runs under the scenario and shows
          you the deltas.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Build a scenario</CardTitle>
          <CardDescription>
            Pick a plan, choose a preset, and adjust the value. Run to see
            the impact, or save the scenario to reuse it later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!hasPlans ? (
            <p className="text-sm text-slate">
              Create a study plan first — the Stress Test needs costs and
              funding to run against.
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-1">
                <label htmlFor="plan" className="text-xs font-medium text-slate">
                  Plan
                </label>
                <select
                  id="plan"
                  className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal focus-visible:outline-none"
                  value={planId}
                  onChange={(e) => setPlanId(e.target.value)}
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="preset" className="text-xs font-medium text-slate">
                  Preset
                </label>
                <select
                  id="preset"
                  className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-midnight focus-visible:border-teal focus-visible:outline-none"
                  value={preset}
                  onChange={(e) => setPreset(e.target.value as StressScenarioKey)}
                  disabled={loadingPresets}
                >
                  {(Object.keys(presets ?? {}) as StressScenarioKey[]).map((k) => (
                    <option key={k} value={k}>
                      {presets?.[k]?.label ?? k}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="value" className="text-xs font-medium text-slate">
                  Value
                </label>
                <Input
                  id="value"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder={preset === "custom" ? "(free-form)" : "25"}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="note" className="text-xs font-medium text-slate">
                  Note (optional)
                </label>
                <Input
                  id="note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Why this scenario matters to you"
                  maxLength={500}
                />
              </div>

              {presets?.[preset] ? (
                <p className="md:col-span-2 text-xs text-slate">
                  {presets[preset].description}
                </p>
              ) : null}

              {error ? (
                <p
                  role="alert"
                  className="md:col-span-2 rounded-md border border-red/20 bg-red/5 px-3 py-2 text-xs text-red"
                >
                  {error}
                </p>
              ) : null}
              {success ? (
                <p
                  role="status"
                  className="md:col-span-2 rounded-md border border-teal-dark/20 bg-mint/40 px-3 py-2 text-xs text-teal-dark"
                >
                  {success}
                </p>
              ) : null}

              <div className="md:col-span-2 flex flex-wrap items-center gap-2">
                <Button type="button" onClick={handleRun} disabled={running}>
                  {running ? "Running…" : "Run scenario"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? "Saving…" : "Save scenario"}
                </Button>
                <Input
                  className="max-w-xs"
                  placeholder="Scenario name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={120}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {scenarios.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Saved scenarios for this plan</CardTitle>
            <CardDescription>
              {loadingScenarios
                ? "Loading…"
                : `${scenarios.length} saved. Pick one to re-run, or delete to remove it.`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col divide-y divide-border">
              {scenarios.map((s) => (
                <li
                  key={s.id}
                  className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-medium text-midnight">{s.name}</p>
                    <p className="text-xs text-slate">
                      {adjustmentToText(s.scenario_key, valueForScenario(s), noteForScenario(s))}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant={selectedScenario === s.id ? "primary" : "secondary"}
                      onClick={() => setSelectedScenario(s.id)}
                    >
                      {selectedScenario === s.id ? "Selected" : "Use"}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => handleDelete(s)}
                    >
                      Delete
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {result ? <ResultPanel result={result} /> : null}
    </div>
  );
}

function buildAdjustment(
  preset: StressScenarioKey,
  value: string,
  note: string,
) {
  switch (preset) {
    case "rent_shock":
      return { type: "rent_increase_pct" as const, value };
    case "scholarship_cut":
      return { type: "scholarship_reduction_pct" as const, value };
    case "tuition_shock":
      return { type: "tuition_increase_pct" as const, value };
    case "living_expense_shock":
      return { type: "living_expense_increase_pct" as const, value };
    case "fx_shock":
      return { type: "fx_shift_pct" as const, value };
    case "family_delay":
      return { type: "family_support_delay_days" as const, value };
    case "custom":
      return { type: "custom_note" as const, value: null, note };
  }
}

function valueForScenario(s: StressScenario): string {
  const adj = s.adjustments[0];
  return adj?.value ?? "";
}

function noteForScenario(s: StressScenario): string {
  const adj = s.adjustments[0];
  return adj?.note ?? "";
}

function ResultPanel({ result }: { result: StressRunResult }) {
  const baseCcy = result.base_currency;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scenario result: {result.scenario_name}</CardTitle>
        <CardDescription>
          Computed at {new Date(result.generated_at).toLocaleString()} ·
          engine {result.calculation_version}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {result.warnings.length > 0 ? (
          <ul className="mb-4 flex flex-col gap-1 rounded-md border border-amber/40 bg-amber/10 p-3 text-xs text-amber">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        ) : null}

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate">
              <th className="py-2">Metric</th>
              <th className="py-2">Baseline</th>
              <th className="py-2">Scenario</th>
              <th className="py-2 text-right">Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {renderRow("Funding gap", result.funding_gap, baseCcy, true)}
            {renderRow("Funding surplus", result.funding_surplus, baseCcy)}
            {renderRow("Upfront cash requirement", result.upfront_cash_requirement, baseCcy, true)}
            {renderRow("Upfront cash gap", result.upfront_cash_gap, baseCcy, true)}
            {renderRow("First-year cost", result.first_year_cost, baseCcy, true)}
            {renderRow("Total projected cost", result.total_projected_cost, baseCcy, true)}
            {renderRow("Confirmed funding (eligible)", result.eligible_confirmed, baseCcy)}
            {renderRow("Confirmed + conditional funding", result.eligible_with_conditional, baseCcy)}
            {renderRow("Available before departure", result.available_before_departure, baseCcy)}
          </tbody>
        </table>

        {result.notes.length > 0 ? (
          <details className="mt-4">
            <summary className="cursor-pointer text-xs text-slate">
              Scenario notes
            </summary>
            <ul className="mt-2 flex flex-col gap-1 text-xs text-slate">
              {result.notes.map((n, i) => (
                <li key={i}>· {n}</li>
              ))}
            </ul>
          </details>
        ) : null}
      </CardContent>
    </Card>
  );
}

function renderRow(
  label: string,
  delta: { baseline: string; scenario: string; delta: string },
  ccy: string,
  emphasize = false,
) {
  const direction = Number(delta.delta) >= 0 ? "+" : "";
  const colour = emphasize
    ? Math.abs(Number(delta.delta)) > 0
      ? "text-amber"
      : "text-slate"
    : "text-slate";
  return (
    <tr>
      <td className={`py-2 ${emphasize ? "font-medium text-midnight" : "text-midnight"}`}>
        {label}
      </td>
      <td className="py-2 text-slate tabular-nums">
        {formatMoney(delta.baseline, ccy)}
      </td>
      <td className="py-2 text-midnight tabular-nums">
        {formatMoney(delta.scenario, ccy)}
      </td>
      <td className={`py-2 text-right tabular-nums ${colour}`}>
        {direction}
        {formatMoney(delta.delta, ccy)}
      </td>
    </tr>
  );
}
