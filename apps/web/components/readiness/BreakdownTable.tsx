"use client";

import * as React from "react";

import { formatMoney } from "@/lib/format";

import type { CostBreakdown, FundingBreakdown } from "@beyond-borders/shared-types";

export function CostBreakdownTable({
  breakdown,
}: {
  breakdown: CostBreakdown;
}) {
  const { base_currency } = breakdown;
  return (
    <table className="w-full text-sm tabular-nums">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase text-slate">
          <th className="py-2 font-medium">Year</th>
          <th className="py-2 text-right font-medium">Recurring</th>
          <th className="py-2 text-right font-medium">One-time</th>
          <th className="py-2 text-right font-medium">Total</th>
        </tr>
      </thead>
      <tbody>
        {breakdown.per_year.map((y) => (
          <tr key={y.year_index} className="border-b border-border/60">
            <td className="py-2">Year {y.year_index}</td>
            <td className="py-2 text-right">
              {formatMoney(y.recurring_total, base_currency)}
            </td>
            <td className="py-2 text-right">
              {formatMoney(y.one_time_total, base_currency)}
            </td>
            <td className="py-2 text-right font-medium text-midnight">
              {formatMoney(y.total, base_currency)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function FundingBreakdownTable({
  funding,
}: {
  funding: FundingBreakdown;
}) {
  const { base_currency } = funding;
  const rows: Array<[string, string]> = [
    ["Confirmed (eligible)", funding.eligible_confirmed],
    ["+ Conditional", funding.conditional_total],
    ["+ Expected (not yet confirmed)", funding.expected_total],
    ["= With conditional & expected", funding.eligible_with_conditional],
    ["Available before departure", funding.available_before_departure],
  ];
  return (
    <table className="w-full text-sm tabular-nums">
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label} className="border-b border-border/60">
            <td className="py-2 text-slate">{label}</td>
            <td className="py-2 text-right font-medium text-midnight">
              {formatMoney(value, base_currency)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
