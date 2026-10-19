/**
 * Sources & Assumptions workspace.
 *
 * Manages a per-user registry of "sources" — labels + URLs that cite
 * where a cost, FX rate, or scholarship number came from. Sources
 * are global to the user (not tied to a plan) so the same university
 * page can be cited from cost items across multiple plans.
 *
 * The page is intentionally lightweight: create / edit / delete a
 * label and an optional URL/notes. The plan/cost/funding pages will
 * later attach a `source_id` to specific rows; for now this gives
 * users a place to capture them in one place.
 */

"use client";

import * as React from "react";

import type {
  DataSource,
  DataSourceCreate,
  DataSourceUpdate,
} from "@beyond-borders/shared-types";

import { ApiClientError } from "@/lib/client-api";
import { sourcesApi } from "@/lib/sources-api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

type DraftSource = {
  id: string | null;
  label: string;
  url: string;
  notes: string;
};

const EMPTY_DRAFT: DraftSource = { id: null, label: "", url: "", notes: "" };

function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiClientError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}

export function SourcesWorkspace() {
  const [sources, setSources] = React.useState<DataSource[]>([]);
  const [draft, setDraft] = React.useState<DraftSource>(EMPTY_DRAFT);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await sourcesApi.list();
      setSources(rows);
    } catch (err) {
      setError(describeError(err, "Could not load your sources."));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  function startEdit(src: DataSource) {
    setDraft({
      id: src.id,
      label: src.label,
      url: src.url ?? "",
      notes: src.notes ?? "",
    });
    setError(null);
    setSuccess(null);
  }

  function resetDraft() {
    setDraft(EMPTY_DRAFT);
    setError(null);
    setSuccess(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const label = draft.label.trim();
    if (label.length === 0) {
      setError("Please enter a label.");
      return;
    }
    if (label.length > 120) {
      setError("Label must be 120 characters or fewer.");
      return;
    }
    const url = draft.url.trim() === "" ? null : draft.url.trim();
    if (url && url.length > 2000) {
      setError("URL must be 2000 characters or fewer.");
      return;
    }
    const notes = draft.notes.trim() === "" ? null : draft.notes.trim();
    if (notes && notes.length > 2000) {
      setError("Notes must be 2000 characters or fewer.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      if (draft.id) {
        const payload: DataSourceUpdate = {
          label,
          url,
          notes,
        };
        const updated = await sourcesApi.update(draft.id, payload);
        setSources((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
        setSuccess(`Updated “${updated.label}”.`);
      } else {
        const payload: DataSourceCreate = { label, url, notes };
        const created = await sourcesApi.create(payload);
        setSources((prev) => [...prev, created]);
        setSuccess(`Saved “${created.label}”.`);
      }
      setDraft(EMPTY_DRAFT);
    } catch (err) {
      setError(describeError(err, "Could not save the source."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(src: DataSource) {
    if (!window.confirm(`Delete source “${src.label}”?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await sourcesApi.remove(src.id);
      setSources((prev) => prev.filter((s) => s.id !== src.id));
      if (draft.id === src.id) setDraft(EMPTY_DRAFT);
      setSuccess(`Deleted “${src.label}”.`);
    } catch (err) {
      setError(describeError(err, "Could not delete the source."));
    }
  }

  const editing = draft.id !== null;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">Sources &amp; Assumptions</h1>
        <p className="text-sm text-slate">
          Every important input is labelled: a verified source, a planning estimate,
          conditional funding, or your own value. Capture them here once and cite
          them from your cost and funding rows.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>{editing ? "Edit source" : "Add a source"}</CardTitle>
          <CardDescription>
            A short label is required. The URL is optional — paste a link to the
            university page, bank statement, or scholarship letter.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
            <div className="flex flex-col gap-1">
              <label
                htmlFor="source-label"
                className="text-xs font-medium text-slate"
              >
                Label
              </label>
              <Input
                id="source-label"
                name="label"
                value={draft.label}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, label: e.target.value }))
                }
                placeholder="Stanford graduate tuition, 2026-27"
                maxLength={120}
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label
                htmlFor="source-url"
                className="text-xs font-medium text-slate"
              >
                URL (optional)
              </label>
              <Input
                id="source-url"
                name="url"
                type="url"
                value={draft.url}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, url: e.target.value }))
                }
                placeholder="https://example.edu/tuition"
                maxLength={2000}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label
                htmlFor="source-notes"
                className="text-xs font-medium text-slate"
              >
                Notes (optional)
              </label>
              <textarea
                id="source-notes"
                name="notes"
                value={draft.notes}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, notes: e.target.value }))
                }
                placeholder="Quoted as USD, includes mandatory fees."
                maxLength={2000}
                rows={3}
                className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-midnight placeholder:text-slate/60 focus:border-teal-dark focus:outline-none focus:ring-2 focus:ring-teal-dark/30"
              />
            </div>

            {error ? (
              <p
                role="alert"
                className="rounded-md border border-red/20 bg-red/5 px-3 py-2 text-xs text-red"
              >
                {error}
              </p>
            ) : null}
            {success ? (
              <p
                role="status"
                className="rounded-md border border-teal-dark/20 bg-mint/40 px-3 py-2 text-xs text-teal-dark"
              >
                {success}
              </p>
            ) : null}

            <div className="flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : editing ? "Save changes" : "Add source"}
              </Button>
              {editing ? (
                <Button type="button" variant="ghost" onClick={resetDraft}>
                  Cancel
                </Button>
              ) : null}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your sources</CardTitle>
          <CardDescription>
            {loading
              ? "Loading…"
              : sources.length === 0
                ? "No sources yet — your first one appears here."
                : `${sources.length} source${sources.length === 1 ? "" : "s"} captured.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sources.length === 0 && !loading ? (
            <p className="text-xs text-slate">
              Once a cost or funding row links to a source, you will be able to
              see it referenced from the Financial Readiness and Funding Plan
              pages.
            </p>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {sources.map((src) => (
                <li
                  key={src.id}
                  className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between"
                >
                  <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-medium text-midnight">{src.label}</p>
                    {src.url ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="break-all text-xs text-teal-dark underline-offset-2 hover:underline"
                      >
                        {src.url}
                      </a>
                    ) : null}
                    {src.notes ? (
                      <p className="text-xs text-slate">{src.notes}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => startEdit(src)}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => handleDelete(src)}
                    >
                      Delete
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
