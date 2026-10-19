import { apiFetch } from "@/lib/api";
import { SpendingWorkspace } from "./SpendingWorkspace";

import type { StudyPlan } from "@beyond-borders/shared-types";

export const metadata = { title: "Spending Tracker" };

export default async function Page() {
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch {
    plans = [];
  }
  return <SpendingWorkspace initialPlans={plans} />;
}
