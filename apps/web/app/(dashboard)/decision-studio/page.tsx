import { apiFetch } from "@/lib/api";
import { DecisionStudioWorkspace } from "./DecisionStudioWorkspace";

import type { StudyPlan } from "@beyond-borders/shared-types";

export const metadata = { title: "Decision Studio" };

export default async function Page() {
  let plans: StudyPlan[] = [];
  try {
    plans = await apiFetch<StudyPlan[]>("/study-plans");
  } catch {
    plans = [];
  }
  return <DecisionStudioWorkspace initialPlans={plans} />;
}
