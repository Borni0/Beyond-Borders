import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { SignOutButton } from "@/components/SignOutButton";
import { apiFetch, ApiClientError } from "@/lib/api";
import { requireUser } from "@/lib/auth";
import { formatDate, formatMoney } from "@/lib/format";

import type {
  ReadinessResult,
  StudyPlan,
} from "@beyond-borders/shared-types";

const REFERENCE_STATUSES = [
  {
    code: "funding-gap",
    title: "Funding gap identified",
    body: "Projected eligible funding is less than projected costs.",
  },
  {
    code: "upfront-cash-gap",
    title: "Upfront cash gap",
    body: "Total funding may cover projected costs, but pre-departure cash is insufficient for immediate expenses.",
  },
  {
    code: "conditional-funding",
    title: "Conditional funding",
    body: "The plan depends on unconfirmed scholarships, loans, income, or contributions.",
  },
  {
    code: "scenario-sensitive",
    title: "Scenario-sensitive",
    body: "The plan develops a material shortfall under one or more selected scenarios.",
  },
  {
    code: "no-modeled-shortfall",
    title: "No modeled shortfall",
    body: "Current inputs cover modeled expenses under the selected assumptions. Not a guarantee of affordability.",
  },
];

async function loadOverviewSummary() {
  // Load plans; if the first plan exists, load its readiness snapshot.
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch (err) {
    if (err instanceof ApiClientError) return { plan: null, readiness: null };
    throw err;
  }
  const plan = plans[0] ?? null;
  if (!plan) return { plan: null, readiness: null };
  let readiness: ReadinessResult | null = null;
  try {
    readiness = await apiFetch<ReadinessResult>(
      `/readiness/${plan.id}`,
    );
  } catch {
    readiness = null;
  }
  return { plan, readiness };
}

export default async function DashboardOverviewPage() {
  const user = await requireUser();
  const { plan, readiness } = await loadOverviewSummary();

  return (
    <div className="flex flex-col gap-8">
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <p className="text-sm text-slate">
            Welcome back, {user.name || user.email}.
          </p>
          <h1 className="text-3xl font-semibold text-midnight">Overview</h1>
        </div>
        <div className="pt-1">
          <SignOutButton />
        </div>
      </header>

      {/* Active plan card */}
      <section aria-labelledby="active-plan" className="flex flex-col gap-3">
        <h2 id="active-plan" className="text-xl font-semibold text-midnight">
          Active plan
        </h2>
        {plan ? (
          <Card>
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <CardDescription>
                {plan.base_currency} · {formatDate(plan.start_date)} →{" "}
                {formatDate(plan.end_date)} ({plan.duration_months} months)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {readiness ? (
                <div className="grid gap-4 sm:grid-cols-3">
                  <Stat
                    label="Projected total cost"
                    value={formatMoney(
                      readiness.breakdown.total_projected_cost,
                      readiness.base_currency,
                    )}
                  />
                  <Stat
                    label="Funding gap"
                    value={formatMoney(
                      readiness.funding_gap,
                      readiness.base_currency,
                    )}
                    tone={
                      Number(readiness.funding_gap) > 0 ? "danger" : "ok"
                    }
                  />
                  <Stat
                    label="Upfront cash gap"
                    value={formatMoney(
                      readiness.upfront_cash_gap,
                      readiness.base_currency,
                    )}
                    tone={
                      Number(readiness.upfront_cash_gap) > 0 ? "warn" : "ok"
                    }
                  />
                </div>
              ) : (
                <p className="text-sm text-slate">
                  Readiness snapshot unavailable. Try opening the plan to refresh.
                </p>
              )}
              <div className="mt-4 flex justify-end">
                <Link
                  href="/readiness"
                  className="text-sm font-medium text-teal hover:underline"
                >
                  Open readiness →
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent>
              <p className="text-sm text-slate">
                No plans yet. Create one from the{" "}
                <Link
                  href="/readiness"
                  className="font-medium text-teal hover:underline"
                >
                  Financial Readiness
                </Link>{" "}
                page to start tracking your study budget.
              </p>
            </CardContent>
          </Card>
        )}
      </section>

      <section aria-labelledby="quick-actions" className="flex flex-col gap-3">
        <h2 id="quick-actions" className="text-xl font-semibold text-midnight">
          Quick actions
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            href="/readiness"
            className="rounded-2xl border border-border bg-white p-4 transition-colors hover:bg-ivory"
          >
            <p className="text-sm font-medium text-midnight">Open Financial Readiness</p>
            <p className="mt-1 text-xs text-slate">Available now in Phase 1.</p>
          </Link>
          <Link
            href="/settings"
            className="rounded-2xl border border-border bg-white p-4 transition-colors hover:bg-ivory"
          >
            <p className="text-sm font-medium text-midnight">Update your profile</p>
            <p className="mt-1 text-xs text-slate">Available now.</p>
          </Link>
        </div>
      </section>

      <section aria-labelledby="statuses" className="flex flex-col gap-3">
        <h2 id="statuses" className="text-xl font-semibold text-midnight">
          How we communicate financial readiness
        </h2>
        <p className="text-sm text-slate">
          Beyond Borders does not produce an unexplained AI readiness percentage.
          Your results are reported using the statuses below (spec §6). A plan
          can carry more than one.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {REFERENCE_STATUSES.map((s) => (
            <Card key={s.code}>
              <CardHeader>
                <CardTitle>{s.title}</CardTitle>
                <CardDescription>{s.body}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-slate">Reference label — not a current result.</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn" | "danger" | "default";
}) {
  const toneClass =
    tone === "danger"
      ? "text-red"
      : tone === "warn"
        ? "text-amber-700"
        : tone === "ok"
          ? "text-teal-dark"
          : "text-midnight";
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate">{label}</p>
      <p className={`text-xl font-semibold tabular-nums ${toneClass}`}>
        {value}
      </p>
    </div>
  );
}
