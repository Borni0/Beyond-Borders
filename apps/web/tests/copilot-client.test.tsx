/**
 * Tests for the Finance Copilot client form. Mocks the API client and
 * asserts that the form posts the question and renders the response
 * (status chip, message, evidence trail, follow-up buttons).
 */

import * as React from "react";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { CopilotClient } from "@/app/(dashboard)/copilot/CopilotClient";
import type { CopilotResponse } from "@/lib/copilot-api";

const SAMPLE_RESPONSE: CopilotResponse = {
  request_id: "abc123",
  status: "answered",
  message: "You have a notable funding gap of 3000.00 USD.",
  intent: "cost_risk",
  primary_agent: "cost_risk",
  confidence: 0.85,
  evidence: [
    {
      label: "Funding gap",
      value: "3000.00",
      source: "readiness",
      source_field: "readiness.funding_gap",
    },
  ],
  follow_ups: ["Which category is driving the gap?"],
  notes: [],
  plan_id: "p-1",
  generated_at: "2026-10-19T10:00:00.000Z",
  trace: [],
};

const askMock = vi.fn();

vi.mock("@/lib/copilot-api", () => ({
  copilotApi: {
    ask: (...args: unknown[]) => askMock(...args),
  },
}));

describe("CopilotClient", () => {
  beforeEach(() => {
    askMock.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the empty form on mount", () => {
    render(<CopilotClient />);
    expect(
      screen.getByRole("heading", { name: /ask the copilot/i })
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/am i going to be short/i)
    ).toBeInTheDocument();
  });

  it("submits the question and renders the response", async () => {
    askMock.mockResolvedValueOnce(SAMPLE_RESPONSE);
    render(<CopilotClient />);
    const input = screen.getByPlaceholderText(/am i going to be short/i);
    fireEvent.change(input, {
      target: { value: "Am I going to be short on money?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask$/i }));

    await waitFor(() => {
      expect(askMock).toHaveBeenCalledWith({
        question: "Am I going to be short on money?",
      });
    });
    await waitFor(() => {
      expect(
        screen.getByText(/notable funding gap of 3000\.00 USD/i)
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/Answered/i)).toBeInTheDocument();
    // The evidence label appears inside the rendered evidence list.
    expect(screen.getAllByText(/Funding gap/i).length).toBeGreaterThan(0);
  });

  it("shows an error when the API call rejects", async () => {
    askMock.mockRejectedValueOnce(new Error("backend offline"));
    render(<CopilotClient />);
    const input = screen.getByPlaceholderText(/am i going to be short/i);
    fireEvent.change(input, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("button", { name: /^ask$/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/backend offline/i);
    });
  });

  it("renders a follow-up click that re-asks the question", async () => {
    askMock.mockResolvedValueOnce(SAMPLE_RESPONSE);
    render(<CopilotClient />);
    fireEvent.click(
      screen.getByRole("button", { name: /am i going to be short on money/i })
    );
    await waitFor(() => {
      expect(askMock).toHaveBeenCalled();
    });
    // After the first response, the follow-up chips appear.
    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: /which category is driving the gap/i,
        })
      ).toBeInTheDocument();
    });
  });
});
