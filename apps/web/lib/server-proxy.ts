/**
 * Shared server-side proxy: forwards a request from the Next.js route
 * handler to the FastAPI backend, preserving the session cookie.
 *
 * All five entity groups (study-plans, costs, funding, sources, fx) use
 * this. We keep it as a single helper so the auth-cookie plumbing lives
 * in one place.
 */

import { NextResponse, type NextRequest } from "next/server";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] as const;
type AllowedMethod = (typeof ALLOWED_METHODS)[number];

function isAllowedMethod(method: string): method is AllowedMethod {
  return (ALLOWED_METHODS as readonly string[]).includes(method);
}

export type ProxyOptions = {
  /** Path under the API base, e.g. "study-plans" or "plans/abc/costs". */
  pathPrefix: string;
  /**
   * Extra path segments extracted from the dynamic route [...path]. These
   * are appended after `pathPrefix`.
   */
  suffix?: string[];
};

export async function proxyToApi(
  request: NextRequest,
  opts: ProxyOptions,
): Promise<NextResponse> {
  const method = request.method.toUpperCase();
  if (!isAllowedMethod(method)) {
    return NextResponse.json(
      { error: { code: "METHOD_NOT_ALLOWED", message: "Method not allowed." } },
      { status: 405 },
    );
  }

  const suffix = (opts.suffix ?? []).join("/");
  const search = request.nextUrl.search ?? "";
  const target = suffix
    ? `${API_BASE_URL}/${opts.pathPrefix}/${suffix}${search}`
    : `${API_BASE_URL}/${opts.pathPrefix}${search}`;

  const headers = new Headers();
  const forward = ["accept", "content-type", "origin", "user-agent"];
  for (const h of forward) {
    const v = request.headers.get(h);
    if (v) headers.set(h, v);
  }
  const cookieHeader = request.headers.get("cookie");
  if (cookieHeader) headers.set("cookie", cookieHeader);

  let body: BodyInit | undefined;
  if (method !== "GET" && method !== "OPTIONS" && method !== "DELETE") {
    const text = await request.text();
    body = text.length > 0 ? text : undefined;
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: request.signal,
    });
  } catch (err) {
    // The backend is down or the connection was refused. Surface a 502 so
    // the client can show a friendly message.
    return NextResponse.json(
      {
        error: {
          code: "UPSTREAM_UNREACHABLE",
          message: "The API is unreachable. Please try again in a moment.",
        },
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) responseHeaders.set("content-type", contentType);
  // Pass through set-cookie (there may be more than one in some flows).
  const setCookie = upstream.headers.getSetCookie?.() ?? [];
  if (setCookie.length === 0) {
    const single = upstream.headers.get("set-cookie");
    if (single) setCookie.push(single);
  }
  for (const c of setCookie) responseHeaders.append("set-cookie", c);

  const payload =
    method === "DELETE" || upstream.status === 204
      ? null
      : await upstream.text();

  return new NextResponse(payload, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
