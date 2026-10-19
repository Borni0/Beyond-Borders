import * as React from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LivingExpensesWorkspace } from "@/app/(dashboard)/living-expenses/LivingExpensesWorkspace";

describe("LivingExpensesWorkspace", () => {
  it("calculates monthly and annual living costs from user input", () => {
    render(<LivingExpensesWorkspace />);

    fireEvent.change(screen.getByLabelText(/monthly rent/i), {
      target: { value: "900" },
    });
    fireEvent.change(screen.getByLabelText(/food & groceries/i), {
      target: { value: "450" },
    });
    fireEvent.change(screen.getByLabelText(/transport/i), {
      target: { value: "140" },
    });
    fireEvent.change(screen.getByLabelText(/utilities & internet/i), {
      target: { value: "110" },
    });
    fireEvent.change(screen.getByLabelText(/insurance & healthcare/i), {
      target: { value: "80" },
    });
    fireEvent.change(screen.getByLabelText(/personal & misc/i), {
      target: { value: "180" },
    });

    fireEvent.click(screen.getByRole("button", { name: /calculate my monthly cost/i }));

    expect(screen.getByText("$1,860.00")).toBeInTheDocument();
    expect(screen.getByText("$22,320.00")).toBeInTheDocument();
    expect(screen.getByText(/monthly living estimate/i)).toBeInTheDocument();
  });

  it("supports destination comparison using country, city, and institution filters", () => {
    render(<LivingExpensesWorkspace />);

    fireEvent.change(screen.getByLabelText(/destination country/i), {
      target: { value: "United Kingdom" },
    });
    fireEvent.change(screen.getByLabelText(/city/i), {
      target: { value: "London" },
    });
    fireEvent.change(screen.getByLabelText(/institution/i), {
      target: { value: "University College London" },
    });

    fireEvent.click(screen.getByRole("button", { name: /compare destination cost/i }));

    expect(screen.getAllByText(/United Kingdom/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/London/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/University College London/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Monthly comparison/i)).toBeInTheDocument();
  });
});
