"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiClientError } from "@/lib/client-api";
import { copilotApi, type CopilotResponse } from "@/lib/copilot-api";

const SUGGESTED_QUESTIONS = [
  "Am I going to be short on money for my plan?",
  "What payments are due soon?",
  "What info am I missing for this plan?",
];

function StatusChip({ status }: { status: CopilotResponse["status"] }) {
  const map: Record<CopilotResponse["status"], string> = {
    answered: "bg-mint text-teal-dark",
    fallback: "bg-amber-100 text-amber-700",
    error: "bg-red-100 text-red-700",
  };
  const labels: Record<CopilotResponse["status"], string> = {
    answered: "Answered",
    fallback: "Needs more info",
    error: "Error",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${map[status]}`}
    >
      {labels[status]}
    </span>
  );
}

export function CopilotClient() {
  const [question, setQuestion] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<CopilotResponse | null>(null);
  const [showTrace, setShowTrace] = useState<boolean>(false);

  async function ask(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await copilotApi.ask({ question: trimmed });
      setResponse(result);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("The copilot could not answer. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Ask the copilot</CardTitle>
          <CardDescription>
            Questions are routed to a specialized agent (cost risk, payment
            planning, or research). Every numeric claim in the answer is
            traced to a field in your own plan.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void ask(question);
            }}
            className="flex flex-col gap-3"
          >
            <label htmlFor="copilot-question" className="text-sm font-medium text-slate">
              Your question
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                id="copilot-question"
                name="question"
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g. Am I going to be short on money?"
                maxLength={2000}
                disabled={submitting}
                className="flex-1"
              />
              <Button type="submit" disabled={submitting || question.trim().length === 0}>
                {submitting ? "Asking…" : "Ask"}
              </Button>
            </div>
            {error ? (
              <p className="text-sm text-red" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-2 pt-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => {
                    setQuestion(q);
                    void ask(q);
                  }}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate transition hover:border-teal hover:text-teal disabled:opacity-50"
                  disabled={submitting}
                >
                  {q}
                </button>
              ))}
            </div>
          </form>
        </CardContent>
      </Card>

      {response ? (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <CardTitle>Answer</CardTitle>
                <StatusChip status={response.status} />
              </div>
              <p className="text-xs text-slate">
                {response.intent} · {response.primary_agent} · confidence{" "}
                {(response.confidence * 100).toFixed(0)}%
              </p>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm leading-relaxed text-slate-900">{response.message}</p>

            {response.evidence.length > 0 ? (
              <div className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">
                  Evidence
                </h3>
                <ul className="flex flex-col gap-1.5">
                  {response.evidence.map((ev, i) => (
                    <li
                      key={`${ev.source_field}-${i}`}
                      className="flex flex-col gap-0.5 rounded-lg border border-slate-200 bg-ivory px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                    >
                      <span className="font-medium text-slate-900">{ev.label}</span>
                      <span className="font-mono text-slate">{ev.value}</span>
                      <span className="text-[10px] text-slate/70">{ev.source_field}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {response.notes.length > 0 ? (
              <div className="flex flex-col gap-1">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">
                  Notes
                </h3>
                <ul className="list-disc pl-5 text-xs text-slate">
                  {response.notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {response.follow_ups.length > 0 ? (
              <div className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">
                  Follow-ups
                </h3>
                <div className="flex flex-wrap gap-2">
                  {response.follow_ups.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => {
                        setQuestion(q);
                        void ask(q);
                      }}
                      className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate transition hover:border-teal hover:text-teal"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="border-t border-slate-200 pt-3">
              <button
                type="button"
                onClick={() => setShowTrace((s) => !s)}
                className="text-xs font-medium text-slate hover:text-teal"
              >
                {showTrace ? "Hide" : "Show"} trace
              </button>
              {showTrace ? (
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] leading-relaxed text-slate">
                  {JSON.stringify(response.trace, null, 2)}
                </pre>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
