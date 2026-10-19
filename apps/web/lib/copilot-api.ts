/**
 * Client for the Finance Copilot multi-agent endpoint.
 *
 * The backend classifies the question, dispatches to a specialized
 * agent, and returns a validated ``CopilotResponse``. The frontend
 * treats that response as the canonical contract — no separate
 * type package is required.
 */

import { apiFetch } from "@/lib/client-api";

export type CopilotEvidence = {
  label: string;
  value: string;
  source: "readiness" | "payment" | "funding" | "plan" | "fx" | "engine";
  source_field: string;
};

export type CopilotStatus = "answered" | "fallback" | "error";

export type CopilotIntent =
  | "cost_risk"
  | "payment_planning"
  | "research"
  | "unknown";

export type CopilotAgentName =
  | "cost_risk"
  | "payment_planning"
  | "research"
  | "evidence_validator";

export type CopilotTraceStep = {
  name: string;
  elapsed_ms: number;
  detail: Record<string, unknown>;
  error: string | null;
};

export type CopilotResponse = {
  request_id: string;
  status: CopilotStatus;
  message: string;
  intent: CopilotIntent;
  primary_agent: CopilotAgentName;
  confidence: number;
  evidence: CopilotEvidence[];
  follow_ups: string[];
  notes: string[];
  plan_id: string | null;
  generated_at: string;
  trace: CopilotTraceStep[];
};

export type CopilotRequest = {
  question: string;
  plan_id?: string;
  upfront_window_days?: number;
};

export const copilotApi = {
  ask: (input: CopilotRequest) =>
    apiFetch<CopilotResponse>("/copilot", { method: "POST", json: input }),
};
