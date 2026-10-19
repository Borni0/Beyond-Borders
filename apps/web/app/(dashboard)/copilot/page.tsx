import { CopilotClient } from "./CopilotClient";

export const metadata = { title: "Finance Copilot" };

export default function Page() {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">Finance Copilot</h1>
        <p className="text-sm text-slate">
          Ask plain-language questions about your plan. The copilot
          classifies your question, dispatches to a specialized agent, and
          cites the source of every number it returns.
        </p>
      </header>
      <CopilotClient />
    </div>
  );
}
