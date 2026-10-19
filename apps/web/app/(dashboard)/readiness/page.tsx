import { apiFetch } from "@/lib/api";
import { ReadinessWorkspace } from "./ReadinessWorkspace";

import type { StudyPlan } from "@beyond-borders/shared-types";

export const metadata = { title: "Financial Readiness" };

export default async function Page() {
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch {
    // If the API is down, render an empty workspace. The client will retry
    // once the user takes an action.
    plans = [];
  }
  const initialPlanId = plans[0]?.id ?? null;
  return <ReadinessWorkspace initialPlans={plans} initialPlanId={initialPlanId} />;
}
