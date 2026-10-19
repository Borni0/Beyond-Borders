# Beyond Borders Multi-Agent System Verification Audit

## Executive verdict

Verdict: PARTIALLY IMPLEMENTED

The repository contains a deterministic finance copilot layer with an orchestrator, specialized agent classes, tools, and strict response contracts, but there is no evidence of a real LLM-backed multi-agent system. The code explicitly documents that the AI copilot is a deterministic Phase 6 implementation and not a live model-driven workflow:

- [services/api/app/services/copilot/__init__.py](services/api/app/services/copilot/__init__.py) states: “No LLM dependency. The repo has no LLM API key configured … Every agent here is a pure function …”
- [README.md](README.md) lists “Phase 6 — AI finance copilot” under “Out of scope this phase”
- Search across the repository found no OpenAI, Anthropic, LangChain, LlamaIndex, or similar provider integration

This is therefore not a genuine multi-AI-agent platform in the ScholarFi sense. It is a deterministic, rule-based dispatcher that routes one user question to one specialized agent and validates output through a schema.

---

## Architecture diagram

```mermaid
flowchart TD
    A[Frontend user question] --> B[apps/web/lib/copilot-api.ts]
    B --> C[apps/web/app/api/copilot/route.ts]
    C --> D[services/api/app/api/v1/copilot.py]
    D --> E[services/api/app/services/copilot/orchestrator.py]
    E --> F[Intent classifier: classify_intent]
    E --> G[Tool runner: list_user_plans / load_plan_summary / compute_readiness / list_upcoming_payments / list_overdue_payments / list_fx_rates]
    G --> H[services/api/app/services/copilot/tools.py]
    H --> I[Deterministic finance services: readiness_service, funding_plan_service]
    E --> J[Agent selector: agent_for_intent]
    J --> K[CostRiskAgent / PaymentPlanningAgent / ResearchAgent]
    K --> L[AgentOutput Pydantic model]
    L --> E
    E --> M[CopilotResponse validated and returned to UI]
    M --> N[apps/web/app/(dashboard)/copilot/CopilotClient.tsx]
```

This is a single orchestration path, not a graph of independent collaborating LLM agents with delegated tasks, parallel workers, or synthesized multi-agent reasoning.

---

## Agent inventory

### 1) Orchestrator

- Name: run / orchestrator
- Source: [services/api/app/services/copilot/orchestrator.py](services/api/app/services/copilot/orchestrator.py)
- Purpose: classify intent, fetch relevant data, select one agent, validate output, and return a structured response
- LLM call: None. It is pure Python logic with regex-based intent detection
- Provider/model: Not applicable. No provider integration exists
- Inputs: CopilotRequest, user_id, DB session
- Outputs: CopilotResponse with status, message, evidence, trace
- Tools available: list_user_plans, load_plan_summary, compute_readiness, compute_funding_plan_summary, list_overdue_payments, list_upcoming_payments, list_fx_rates
- Agent-to-agent behavior: No; it selects one agent only
- Error handling: catches exceptions from tools and agents, downgrades to fallback, enforces confidence floor
- Runtime evidence: the copilot tests confirm it returns a valid response and fallback behavior regardless of malformed outputs: [services/api/app/tests/finance/test_copilot_orchestrator.py](services/api/app/tests/finance/test_copilot_orchestrator.py), [services/api/app/tests/api/test_copilot.py](services/api/app/tests/api/test_copilot.py)

### 2) CostRiskAgent

- Name: CostRiskAgent
- Source: [services/api/app/services/copilot/agents.py](services/api/app/services/copilot/agents.py)
- Purpose: answer whether the plan is under-funded or at risk
- LLM call: None. The implementation directly inspects readiness snapshots and computes answer strings from fields like funding_gap and upfront_cash_gap
- Inputs: AgentContext with plan_summary, readiness, funding_summary, payment data, FX rates
- Outputs: AgentOutput with answer, confidence, evidence, notes
- Tools available: none directly; it consumes pre-fetched context produced by the orchestrator
- Agent-to-agent handoff: none
- Error handling: returns a safe no-data answer if readiness or plan is missing
- Evidence: reads readiness data and emits evidence records with source_field values such as readiness.funding_gap

### 3) PaymentPlanningAgent

- Name: PaymentPlanningAgent
- Source: [services/api/app/services/copilot/agents.py](services/api/app/services/copilot/agents.py)
- Purpose: answer what is overdue or due soon
- LLM call: None. It aggregates overdue and upcoming payment events from the database
- Inputs: payments_overdue, payments_upcoming, optional plan summary
- Outputs: AgentOutput with payment summary and evidence
- Tools available: none directly; it consumes tool output from the orchestrator
- Agent-to-agent handoff: none
- Error handling: returns a no-events guidance message if none are present

### 4) ResearchAgent

- Name: ResearchAgent
- Source: [services/api/app/services/copilot/agents.py](services/api/app/services/copilot/agents.py)
- Purpose: explain missing inputs or FX gaps
- LLM call: None. It analyzes already-loaded data and prepares a human-readable summary
- Inputs: FX rates, readiness, funding summary
- Outputs: AgentOutput with missing data notes and follow-ups
- Tools available: none directly
- Agent-to-agent handoff: none
- Error handling: handles missing FX data by returning a guidance answer rather than failing

### 5) Evidence validator / placeholder

- Name: EVIDENCE_VALIDATOR appears in [services/api/app/services/copilot/contracts.py](services/api/app/services/copilot/contracts.py)
- Status: declared in the enum but not implemented as a concrete agent class or runtime executor
- Meaning: there is an enum entry for a potential agent, but no actual agent implementation or orchestration step uses it

This is important because the product presents “agent” names and “multi-agent” branding, but the active execution path does not instantiate multiple collaborating agents in one request.

---

## End-to-end request trace

### Actual observed path for a user request

1. User enters a question in the Finance Copilot UI at [apps/web/app/(dashboard)/copilot/CopilotClient.tsx](apps/web/app/(dashboard)/copilot/CopilotClient.tsx)
2. The front-end calls the API client in [apps/web/lib/copilot-api.ts](apps/web/lib/copilot-api.ts)
3. The browser posts to the Next.js proxy route in [apps/web/app/api/copilot/route.ts](apps/web/app/api/copilot/route.ts)
4. The backend FastAPI route receives the request in [services/api/app/api/v1/copilot.py](services/api/app/api/v1/copilot.py)
5. The route calls run_copilot from [services/api/app/services/copilot/__init__.py](services/api/app/services/copilot/__init__.py)
6. The orchestrator in [services/api/app/services/copilot/orchestrator.py](services/api/app/services/copilot/orchestrator.py) executes the following steps:
   - classify_intent(question)
   - optionally select a plan
   - fetch plan + readiness + funding + payments + FX data through tools in [services/api/app/services/copilot/tools.py](services/api/app/services/copilot/tools.py)
   - instantiate exactly one agent via agent_for_intent(intent)
   - run that single agent’s run(ctx)
   - validate AgentOutput with Pydantic
   - enforce confidence floor and produce CopilotResponse
7. The response is returned to the UI and rendered in [apps/web/app/(dashboard)/copilot/CopilotClient.tsx](apps/web/app/(dashboard)/copilot/CopilotClient.tsx)

### Missing steps relative to a real ScholarFi-style multi-agent workflow

The following elements are absent or explicitly not implemented:

- no parallel execution of independent agents
- no agent-to-agent messaging or shared memory queue
- no delegated sub-tasks between specialist agents
- no result aggregation from multiple agents into a final synthesis step
- no external LLM call, prompt routing, tool-calling loop, or provider-level tracing
- no retries with different model providers when one fails
- no real workflow graph beyond a single intent-based routing decision
- no conversation state or memory persistence beyond the user-owned DB records

The code confirms this is a single-agent dispatch system, not a real collaborative agent swarm.

---

## Runtime and test results

### Actual test evidence

The repository includes copilot-focused tests that verify the orchestrator, route contract, and fallback behavior:

- [services/api/app/tests/finance/test_copilot_orchestrator.py](services/api/app/tests/finance/test_copilot_orchestrator.py)
- [services/api/app/tests/api/test_copilot.py](services/api/app/tests/api/test_copilot.py)

I executed:

- cd /home/borni/finTech/services/api && pytest app/tests/api/test_copilot.py app/tests/finance/test_copilot_orchestrator.py -q

Result:

- 16 tests passed
- output ended with “................ [100%]”

I also executed the frontend suite:

- cd /home/borni/finTech && npm test -w apps/web -- --run

Result:

- 15 test files passed
- 51 tests passed

This is strong evidence that the current implementation behaves consistently as a deterministic orchestration layer. It does not prove external model execution or real multi-agent collaboration.

### Runtime evidence from the code itself

The active code path is not calling a remote model. The architecture statements are explicit:

- [services/api/app/services/copilot/__init__.py](services/api/app/services/copilot/__init__.py) says “No LLM dependency” and “every agent here is a pure function”
- [services/api/app/services/copilot/orchestrator.py](services/api/app/services/copilot/orchestrator.py) describes intent classification and tool-bound logic, not model calls
- There are no OpenAI or provider SDK dependencies in the project manifests and no matches for provider libraries in the codebase

### What cannot be verified here

The audit did not find any runtime evidence of:

- model inference requests
- provider logs
- asynchronous concurrent agent workers
- tool calls delegated to multiple independent agents
- multi-agent synthesis across different model prompts

Because no model provider is configured and no LLM integration is present, those claims would be unsupported.

---

## Separation between LLM agents and deterministic financial services

### Deterministic financial services

These are real domain services and they are the actual computational engine underpinning the financial logic:

- [services/api/app/services/financial/readiness.py](services/api/app/services/financial/readiness.py)
- [services/api/app/services/financial/projection.py](services/api/app/services/financial/projection.py)
- [services/api/app/services/decision_studio_service.py](services/api/app/services/decision_studio_service.py)
- [services/api/app/services/stress_test_service.py](services/api/app/services/stress_test_service.py)

The copilot tools in [services/api/app/services/copilot/tools.py](services/api/app/services/copilot/tools.py) call those deterministic services such as readiness_service and funding_plan_service. That is the data source layer behind the copilot.

### Agent layer

The agent layer is a thin, rule-based wrapper over those results. It is not an LLM orchestration engine. It creates an AgentOutput model, validates it, and returns traceable evidence.

### Why this matters

A financial calculation engine, a readiness snapshot, and a rule-based dispatcher are not automatically equivalent to a multi-AI-agent system. In this repository they are separate layers, and the agent layer is not model-backed.

---

## Missing components relative to the ScholarFi-style workflow

To match a genuine ScholarFi-style multi-agent workflow, the product would need at least:

1. Real LLM provider integration with model configuration and secrets management
2. Multiple autonomous agents with separate roles, memory, and task handoff
3. Parallel execution and concurrency controls
4. A shared state store for agent context and task results
5. Validation of agent outputs against ground truth and cross-checks between agents
6. External tool calling for live research, market data, or FX rates
7. Aggregation and conflict resolution between competing recommendations
8. Retries, timeout escalation, and fallback to another agent or provider
9. Observability: trace IDs, structured logs, provider request IDs, and execution timing across agents

None of these are present in the codebase inspection.

---

## Security, reliability, and data-quality issues

### Security

- The product enforces per-user authorization and DB filtering via user_id in the tool layer, which is good practice: [services/api/app/services/copilot/tools.py](services/api/app/services/copilot/tools.py)
- However, there is no sensitive provider or secret handling for an LLM flow because no actual LLM provider is configured
- The code avoids exposing raw DB objects and uses Pydantic validation for API payloads: [services/api/app/services/copilot/contracts.py](services/api/app/services/copilot/contracts.py)

### Reliability

- The orchestrator has tool caps and a fallback path: [services/api/app/services/copilot/orchestrator.py](services/api/app/services/copilot/orchestrator.py)
- Tool timeouts are approximated with a wall-clock check and graceful degradation
- The code handles malformed agent output by converting it to a fallback response rather than crashing

### Data quality

- The system is deterministic and evidence-backed within a user-owned plan, which is a strength
- However, the “agents” do not check for contradictory recommendations from multiple independent sources because there is no multi-agent synthesis engine
- Missing or incomplete data is surfaced as guidance, not as a high-confidence recommendation

---

## Recommended implementation plan, prioritized by impact

### Priority 1 — Decide the product target

Choose one of two designs and implement to that target:

- Real AI agent platform: integrate a provider, define multiple autonomous agents, a workflow graph, and orchestration service
- Deterministic finance copilot: keep the rule-based system but rename and document it accurately as a structured advisory engine rather than an AI-agent architecture

### Priority 2 — If the goal is a real multi-agent system

1. Introduce provider integration for a real model (OpenAI, Anthropic, Azure OpenAI, or equivalent) behind a dedicated service layer
2. Define explicit agent roles such as planner, cost analyst, FX risk analyst, payment scheduler, and synthesizer
3. Add a shared memory/context object and task queue
4. Add result validation and conflict detection between parallel agent outputs
5. Add provider request logging, trace IDs, and failure-to-fallback paths
6. Add integration tests that verify the full orchestration path with real model mocks or recorded fixtures

### Priority 3 — If the goal is to keep the current architecture

1. Rename the UI and docs to emphasize “deterministic finance copilot” instead of “AI agent” or “multi-agent” language
2. Keep the evidence trail and validation contract
3. Add explicit documentation that the system does not perform LLM reasoning and does not simulate independent agent collaboration
4. Expand deterministic tests around financial correctness and data quality

---

## Bottom line

The repository does not contain a genuine multi-AI-agent workflow consistent with a full ScholarFi-style concept. What it does contain is a deterministic finance copilot with:

- a keyword-based intent classifier
- a centralized orchestrator
- specialized rule-based agents
- tool calls into deterministic backend services
- structured output validation and fallback handling

That is useful and testable, but it is not an LLM-powered multi-agent system.
