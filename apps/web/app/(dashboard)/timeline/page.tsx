import { apiFetch } from "@/lib/api";
import { TimelineWorkspace } from "./TimelineWorkspace";

import type { StudyPlan } from "@beyond-borders/shared-types";

export const metadata = { title: "Financial Timeline" };

export default async function Page() {
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch {
    plans = [];
  }
  const initialPlanId = plans[0]?.id ?? null;
  return (
    <TimelineWorkspace initialPlans={plans} initialPlanId={initialPlanId} />
  );
}
