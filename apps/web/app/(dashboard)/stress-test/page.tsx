import { apiFetch } from "@/lib/api";
import { StressTestWorkspace } from "./StressTestWorkspace";

import type { StudyPlan } from "@beyond-borders/shared-types";

export const metadata = { title: "Stress Test" };

export default async function Page() {
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch {
    plans = [];
  }
  return <StressTestWorkspace initialPlans={plans} />;
}
