/**
 * Users proxy: forwards requests from the browser to the FastAPI backend.
 *
 * Used by the settings page (PATCH /api/v1/users/me). Same pattern as the
 * auth proxy in app/api/auth/[...]/route.ts.
 */

import { NextResponse, type NextRequest } from "next/server";

import { copySetCookieHeaders } from "@/lib/cookies";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ALLOWED_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"] as const;
type AllowedMethod = (typeof ALLOWED_METHODS)[number];

function isAllowedMethod(method: string): method is AllowedMethod {
  return (ALLOWED_METHODS as readonly string[]).includes(method);
}

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const params = await context.params;
  const segments = (params.path ?? []).join("/");
  const search = request.nextUrl.search ?? "";
  const target = `${API_BASE_URL}/users/${segments}${search}`;

  const method = request.method.toUpperCase();
  if (!isAllowedMethod(method)) {
    return NextResponse.json(
      { error: { code: "METHOD_NOT_ALLOWED", message: "Method not allowed." } },
      { status: 405 },
    );
  }

  const headers = new Headers();
  const forward = ["accept", "content-type", "origin", "user-agent"];
  for (const h of forward) {
    const v = request.headers.get(h);
    if (v) headers.set(h, v);
  }
  const cookieHeader = request.headers.get("cookie");
  if (cookieHeader) headers.set("cookie", cookieHeader);

  let body: BodyInit | undefined;
  if (method !== "GET" && method !== "OPTIONS") {
    const text = await request.text();
    body = text.length > 0 ? text : undefined;
  }

  const upstream = await fetch(target, {
    method,
    headers,
    body,
    cache: "no-store",
    signal: request.signal,
  });

  const responseHeaders = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) responseHeaders.set("content-type", contentType);
  copySetCookieHeaders(upstream.headers, responseHeaders);

  const payload =
    method === "DELETE" || upstream.status === 204 ? null : await upstream.text();

  return new NextResponse(payload, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;