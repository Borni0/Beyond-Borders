/**
 * Server-side helpers for talking to the FastAPI backend.
 *
 * These run on the Next.js server (route handlers, server components,
 * server actions). They forward the incoming request's `Cookie` header so
 * the session cookie is preserved end-to-end.
 */

import { cookies, headers } from "next/headers";

import type { ApiError, User } from "@beyond-borders/shared-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
  cache?: RequestCache;
  next?: { revalidate?: number; tags?: string[] };
};

async function buildHeaders(init?: RequestOptions): Promise<Headers> {
  const h = new Headers(init?.headers);
  if (!h.has("Accept")) h.set("Accept", "application/json");

  // Forward the user's cookies so the session is sent.
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c: { name: string; value: string }) => `${c.name}=${c.value}`)
    .join("; ");
  if (cookieHeader) h.set("Cookie", cookieHeader);

  // Echo the request's origin so CORS is happy in dev.
  const headerStore = await headers();
  const origin = headerStore.get("origin");
  if (origin && !h.has("Origin")) h.set("Origin", origin);

  return h;
}

export async function apiFetch<T>(
  path: string,
  init: RequestOptions = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const { json, headers: extraHeaders, cache, next, ...rest } = init;

  const requestHeaders = await buildHeaders({ headers: extraHeaders });
  let body: BodyInit | undefined;
  if (json !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }

  const response = await fetch(url, {
    ...rest,
    headers: requestHeaders,
    body,
    cache: cache ?? "no-store",
    next,
  });

  if (response.status === 204) {
    return undefined as T;
  }

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

/** Convenience: read the current user, returning null if unauthenticated. */
export async function getCurrentUser(): Promise<User | null> {
  try {
    return await apiFetch<User>("/users/me");
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 401) return null;
    throw err;
  }
}