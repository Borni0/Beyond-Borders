"use client";

import * as React from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { StatusChip } from "@/components/readiness/StatusChip";
import {
  CostBreakdownTable,
  FundingBreakdownTable,
} from "@/components/readiness/BreakdownTable";
import { formatMoney, formatPercent } from "@/lib/format";

import type { ReadinessResult } from "@beyond-borders/shared-types";

export function ReadinessPanel({ result }: { result: ReadinessResult }) {
  const base = result.base_currency;
  // Top-of-stack reminder: this panel never renders a single misleading
  // score. Each card is a separate signal; the user should not collapse
  // them into a pass/fail number.
  const signals = describeSignals(result);
  return (
    <div className="flex flex-col gap-6">
      {/* Headline — five cards, no single composite score. */}
      <div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5"
        data-testid="readiness-headline"
      >
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate">
              First-year cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-2xl font-semibold tabular-nums text-midnight"
              data-testid="first-year-cost"
            >
              {formatMoney(result.breakdown.first_year_cost, base)}
            </p>
            <p className="mt-1 text-xs text-slate">
              of {formatMoney(result.breakdown.total_projected_cost, base)} total
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate">
              Projected total cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-2xl font-semibold tabular-nums text-midnight"
              data-testid="total-cost"
            >
              {formatMoney(result.breakdown.total_projected_cost, base)}
            </p>
            {Number(result.breakdown.refundable_deposits) > 0 ? (
              <p className="mt-1 text-xs text-slate">
                + {formatMoney(result.breakdown.refundable_deposits, base)} refundable
              </p>
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate">
              Funding gap
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-2xl font-semibold tabular-nums"
              data-testid="funding-gap"
            >
              {Number(result.funding_gap) > 0 ? (
                <span className="text-red">{formatMoney(result.funding_gap, base)}</span>
              ) : (
                <span className="text-teal-dark">
                  {formatMoney(result.funding_gap, base)}
                </span>
              )}
            </p>
            {Number(result.funding_surplus) > 0 ? (
              <p className="mt-1 text-xs text-teal-dark">
                Surplus {formatMoney(result.funding_surplus, base)}
              </p>
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate">
              Coverage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-2xl font-semibold tabular-nums text-midnight"
              data-testid="coverage-pct"
            >
              {formatPercent(result.coverage_pct)}
            </p>
            <p className="mt-1 text-xs text-slate">
              eligible funding / total cost
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate">
              Upfront cash gap ({result.upfront_cash_window_days}d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-2xl font-semibold tabular-nums"
              data-testid="upfront-gap"
            >
              {Number(result.upfront_cash_gap) > 0 ? (
                <span className="text-amber-700">
                  {formatMoney(result.upfront_cash_gap, base)}
                </span>
              ) : (
                <span className="text-teal-dark">
                  {formatMoney(result.upfront_cash_gap, base)}
                </span>
              )}
            </p>
            <p className="mt-1 text-xs text-slate">
              Need {formatMoney(result.upfront_cash_requirement, base)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Secondary signal row: first-year gap + potential gap if pending funds don't arrive. */}
      {(Number(result.first_year_funding_gap) > 0 ||
        Number(result.potential_gap_after_expected) > 0) && (
        <div
          className="grid gap-4 sm:grid-cols-2"
          data-testid="readiness-secondary"
        >
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-slate">
                First-year funding gap
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p
                className="text-xl font-semibold tabular-nums text-midnight"
                data-testid="first-year-funding-gap"
              >
                {formatMoney(result.first_year_funding_gap, base)}
              </p>
              <p className="mt-1 text-xs text-slate">
                What year-1 costs alone still need after confirmed funding.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-slate">
                Worst-case gap if pending funds fall through
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p
                className="text-xl font-semibold tabular-nums text-red"
                data-testid="potential-gap"
              >
                {formatMoney(result.potential_gap_after_expected, base)}
              </p>
              <p className="mt-1 text-xs text-slate">
                If every conditional / expected source is unfulfilled.
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Status chips */}
      {result.statuses.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2" data-testid="status-chips">
              {result.statuses.map((code) => (
                <StatusChip key={code} code={code} />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Read-only checklist — the user-facing interpretation of the
          signals above. Each item is a check that's already been
          applied to the math; nothing here adds new rules. */}
      <Card>
        <CardHeader>
          <CardTitle>Readiness checklist</CardTitle>
          <p className="text-sm text-slate">
            A transparent reading of your inputs — not a single score.
          </p>
        </CardHeader>
        <CardContent>
          <ul className="flex flex-col gap-2 text-sm" data-testid="readiness-checklist">
            {signals.map((s) => (
              <li
                key={s.label}
                className={
                  "flex items-start justify-between gap-3 rounded border border-border/60 px-3 py-2 " +
                  (s.ok ? "bg-mint/30" : "bg-ivory")
                }
              >
                <span className="flex-1 text-midnight">{s.label}</span>
                <span
                  className={
                    "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium " +
                    (s.ok
                      ? "bg-teal-dark/10 text-teal-dark"
                      : "bg-amber-100 text-amber-700")
                  }
                >
                  {s.ok ? "OK" : "Action"}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Missing inputs */}
      {result.missing_inputs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Add the following to finalize</CardTitle>
          </CardHeader>
          <CardContent>
            <ul
              className="list-inside list-disc text-sm text-slate"
              data-testid="missing-inputs"
            >
              {result.missing_inputs.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {/* Breakdown tables */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Costs by year ({base})</CardTitle>
          </CardHeader>
          <CardContent>
            <CostBreakdownTable breakdown={result.breakdown} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Funding ({base})</CardTitle>
          </CardHeader>
          <CardContent>
            <FundingBreakdownTable funding={result.funding} />
          </CardContent>
        </Card>
      </div>

      {/* Per-category totals */}
      {Object.keys(result.breakdown.per_category).length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Costs by category ({base})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 text-sm tabular-nums sm:grid-cols-3">
              {Object.entries(result.breakdown.per_category)
                .sort(([, a], [, b]) => Number(b) - Number(a))
                .map(([cat, amount]) => (
                  <div
                    key={cat}
                    className="flex items-center justify-between rounded border border-border/60 px-3 py-2"
                  >
                    <span className="text-slate">{cat.replace(/_/g, " ")}</span>
                    <span className="font-medium text-midnight">
                      {formatMoney(amount, base)}
                    </span>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Notes */}
      {result.notes.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-inside list-disc text-sm text-slate">
              {result.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

/**
 * Derive a flat list of "things the user has / hasn't covered" from the
 * structured signals we already computed. Each item is derived — no new
 * rules live here.
 */
function describeSignals(result: ReadinessResult): Array<{
  label: string;
  ok: boolean;
}> {
  const out: Array<{ label: string; ok: boolean }> = [];

  out.push({
    label: "Tuition and cost items are entered.",
    ok: result.missing_inputs.every((m) => !m.toLowerCase().includes("cost item")),
  });
  out.push({
    label: "At least one confirmed funding source is recorded.",
    ok: Number(result.funding.confirmed_total) > 0,
  });
  out.push({
    label: `Projected cost is covered by confirmed funding (gap: ${result.funding_gap} ${result.base_currency}).`,
    ok: Number(result.funding_gap) === 0,
  });
  out.push({
    label: `First-year cost is covered (gap: ${result.first_year_funding_gap} ${result.base_currency}).`,
    ok: Number(result.first_year_funding_gap) === 0,
  });
  out.push({
    label: `Upfront window (${result.upfront_cash_window_days} days) cash requirement is covered (gap: ${result.upfront_cash_gap} ${result.base_currency}).`,
    ok: Number(result.upfront_cash_gap) === 0,
  });
  out.push({
    label: "All non-base currencies have an FX rate.",
    ok: result.missing_inputs.every((m) => !m.toLowerCase().includes("fx rate")),
  });

  return out;
}
