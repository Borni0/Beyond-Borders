/**
 * Tests for the Sources & Assumptions workspace.
 *
 * Mocks the API client, mounts the workspace, and verifies the
 * list/create/edit/delete flows plus error display.
 */

import * as React from "react";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SourcesWorkspace } from "@/app/(dashboard)/sources/SourcesWorkspace";
import type { DataSource } from "@beyond-borders/shared-types";

const SOURCE_A: DataSource = {
  id: "11111111-1111-1111-1111-111111111111",
  label: "Stanford tuition page",
  url: "https://example.edu/tuition",
  notes: "USD, mandatory fees included.",
  created_at: "2026-10-19T10:00:00.000Z",
  updated_at: "2026-10-19T10:00:00.000Z",
};

const SOURCE_B: DataSource = {
  id: "22222222-2222-2222-2222-222222222222",
  label: "Bank statement",
  url: null,
  notes: null,
  created_at: "2026-10-19T10:00:00.000Z",
  updated_at: "2026-10-19T10:00:00.000Z",
};

type ListFn = () => Promise<DataSource[]>;
type CreateFn = (input: unknown) => Promise<DataSource>;
type UpdateFn = (id: string, input: unknown) => Promise<DataSource>;
type RemoveFn = (id: string) => Promise<void>;

const mocks = vi.hoisted(() => ({
  list: vi.fn<ListFn>(),
  create: vi.fn<CreateFn>(),
  update: vi.fn<UpdateFn>(),
  remove: vi.fn<RemoveFn>(),
}));

vi.mock("@/lib/sources-api", () => ({
  sourcesApi: {
    list: mocks.list,
    create: mocks.create,
    update: mocks.update,
    remove: mocks.remove,
  },
}));

describe("SourcesWorkspace", () => {
  beforeEach(() => {
    mocks.list.mockReset();
    mocks.create.mockReset();
    mocks.update.mockReset();
    mocks.remove.mockReset();
    mocks.list.mockResolvedValue([SOURCE_A, SOURCE_B]);
    mocks.create.mockImplementation(async (input: unknown) => ({
      id: "33333333-3333-3333-3333-333333333333",
      label: (input as { label: string }).label,
      url: (input as { url?: string | null }).url ?? null,
      notes: (input as { notes?: string | null }).notes ?? null,
      created_at: "2026-10-19T11:00:00.000Z",
      updated_at: "2026-10-19T11:00:00.000Z",
    }));
    mocks.update.mockImplementation(
      async (id: string, input: unknown) => ({
        id,
        label: (input as { label?: string }).label ?? SOURCE_A.label,
        url: (input as { url?: string | null }).url ?? SOURCE_A.url,
        notes: (input as { notes?: string | null }).notes ?? SOURCE_A.notes,
        created_at: SOURCE_A.created_at,
        updated_at: "2026-10-19T11:00:00.000Z",
      }),
    );
    mocks.remove.mockResolvedValue(undefined);
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads and renders the existing sources on mount", async () => {
    render(<SourcesWorkspace />);
    expect(screen.getByRole("heading", { name: /sources & assumptions/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Stanford tuition page")).toBeInTheDocument();
    });
    expect(screen.getByText("Bank statement")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledTimes(1);
  });

  it("creates a new source through the form", async () => {
    render(<SourcesWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Stanford tuition page")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/label/i), {
      target: { value: "Scholarship award letter" },
    });
    fireEvent.change(screen.getByLabelText(/url/i), {
      target: { value: "https://example.com/award" },
    });
    fireEvent.change(screen.getByLabelText(/notes/i), {
      target: { value: "Covers 50% of tuition." },
    });
    fireEvent.click(screen.getByRole("button", { name: /add source/i }));

    await waitFor(() => {
      expect(mocks.create).toHaveBeenCalledWith({
        label: "Scholarship award letter",
        url: "https://example.com/award",
        notes: "Covers 50% of tuition.",
      });
    });
    await waitFor(() => {
      expect(screen.getByText(/saved “scholarship award letter”/i)).toBeInTheDocument();
    });
  });

  it("refuses to submit when the label is empty", async () => {
    render(<SourcesWorkspace />);
    await waitFor(() => {
      expect(screen.getByText("Stanford tuition page")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /add source/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/please enter a label/i);
    });
    expect(mocks.create).not.toHaveBeenCalled();
  });

  it("loads a row into the form for editing and saves the change", async () => {
    render(<SourcesWorkspace />);
    await waitFor(() => {
      expect(screen.getByText("Stanford tuition page")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /^edit$/i });
    expect(editButtons.length).toBeGreaterThan(0);
    fireEvent.click(editButtons[0]!);

    const labelInput = screen.getByLabelText(/label/i) as HTMLInputElement;
    expect(labelInput.value).toBe("Stanford tuition page");

    fireEvent.change(labelInput, { target: { value: "Stanford (updated)" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mocks.update).toHaveBeenCalledWith(
        SOURCE_A.id,
        expect.objectContaining({ label: "Stanford (updated)" }),
      );
    });
  });

  it("deletes a source after confirm", async () => {
    render(<SourcesWorkspace />);
    await waitFor(() => {
      expect(screen.getByText("Bank statement")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole("button", { name: /^delete$/i });
    expect(deleteButtons.length).toBeGreaterThan(1);
    fireEvent.click(deleteButtons[1]!);

    await waitFor(() => {
      expect(mocks.remove).toHaveBeenCalledWith(SOURCE_B.id);
    });
  });
});
