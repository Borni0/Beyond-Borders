import { apiFetch } from "@/lib/api";
import { FundingPlanWorkspace } from "./FundingPlanWorkspace";

import type { StudyPlan } from "@beyond-borders/shared-types";

export const metadata = { title: "Funding Plan" };

export default async function Page() {
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch {
    plans = [];
  }
  const initialPlanId = plans[0]?.id ?? null;
  return (
    <FundingPlanWorkspace initialPlans={plans} initialPlanId={initialPlanId} />
  );
}
