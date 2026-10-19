/**
 * Copilot proxy: /api/copilot → /api/v1/copilot
 *
 * The browser posts a question; the backend runs the multi-agent
 * pipeline and returns the validated response. This proxy just forwards
 * the request and the Set-Cookie (so the auth session stays attached).
 */

import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(request: NextRequest) {
  return proxyToApi(request, { pathPrefix: "copilot" });
}

export const POST = handle;
export const OPTIONS = handle;
