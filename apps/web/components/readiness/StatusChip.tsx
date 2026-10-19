"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import { STATUS_META } from "@/lib/readiness-types";

import type { ReadinessStatusCode } from "@beyond-borders/shared-types";

const toneClasses: Record<string, string> = {
  ok: "bg-mint/40 text-teal-dark border-teal/30",
  warn: "bg-amber-50 text-amber-700 border-amber-200",
  danger: "bg-red-50 text-red-700 border-red-200",
  info: "bg-slate-50 text-slate-700 border-slate-200",
  muted: "bg-slate-50 text-slate-500 border-slate-200",
};

export function StatusChip({ code }: { code: ReadinessStatusCode }) {
  const meta = STATUS_META[code];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[meta.tone] ?? toneClasses.muted,
      )}
      title={meta.description}
    >
      {meta.label}
    </span>
  );
}
