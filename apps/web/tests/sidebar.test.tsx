import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

import { Sidebar } from "@/components/nav/Sidebar";
import { NAV_ITEMS } from "@/components/nav/nav-items";

describe("Sidebar", () => {
  it("renders every nav item from the spec", () => {
    render(<Sidebar />);
    for (const item of NAV_ITEMS) {
      expect(screen.getByText(item.label)).toBeInTheDocument();
    }
  });

  it("marks the current page with aria-current", () => {
    render(<Sidebar />);
    const overview = screen.getByText("Overview").closest("a");
    expect(overview).toHaveAttribute("aria-current", "page");
  });
});
