/**
 * Funding proxy: /api/funding/... → /api/v1/plans/{planId}/funding/...
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] | undefined }> },
) {
  const params = await context.params;
  const segments: string[] = params.path ?? [];
  if (segments.length === 0) {
    return new Response(
      JSON.stringify({ error: { code: "NOT_FOUND", message: "Plan id required." } }),
      { status: 404, headers: { "content-type": "application/json" } },
    );
  }
  const planId = segments[0]!;
  const rest = segments.slice(1);
  const suffix: string[] = rest.length > 0
    ? [planId, "funding", ...rest]
    : [planId, "funding"];
  return proxyToApi(request, { pathPrefix: "plans", suffix });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
