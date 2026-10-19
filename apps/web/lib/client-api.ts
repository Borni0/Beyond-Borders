/**
 * Client-safe API helpers for browser components.
 *
 * These are intentionally free of `next/headers` / `cookies`; they must only
 * be imported by client components or shared browser code.
 */

import type { ApiError } from "@beyond-borders/shared-types";

export class ApiClientError extends Error {
  status: number;
  body: ApiError | undefined;

  constructor(status: number, message: string, body?: ApiError) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.body = body;
  }
}

type RequestOptions = Omit<RequestInit, "headers" | "body"> & {
  json?: unknown;
  headers?: Record<string, string>;
};

function toApiUrl(path: string): string {
  if (path.startsWith("http")) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return normalized.startsWith("/api") ? normalized : `/api${normalized}`;
}

export async function apiFetch<T>(
  path: string,
  init: RequestOptions = {},
): Promise<T> {
  const url = toApiUrl(path);
  const { json, headers: extraHeaders, ...rest } = init;

  const requestHeaders = new Headers(extraHeaders);
  if (!requestHeaders.has("Accept")) requestHeaders.set("Accept", "application/json");

  let body: BodyInit | undefined;
  if (json !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }

  const response = await fetch(url, {
    ...rest,
    headers: requestHeaders,
    body,
    cache: "no-store",
  });

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const err = (data as { error?: ApiError["error"] } | null)?.error;
    const message =
      err?.message ??
      (response.status === 401
        ? "Authentication required."
        : "Request failed. Please try again.");
    throw new ApiClientError(response.status, message, err as ApiError | undefined);
  }

  return data as T;
}
