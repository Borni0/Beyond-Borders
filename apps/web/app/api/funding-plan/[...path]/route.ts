/**
 * Funding-plan proxy: /api/funding-plan/{planId}/... → /api/v1/plans/{planId}/funding-plan/...
 *
 * Used by the funding-plan and timeline pages for the summary, timeline,
 * convert, and export.csv endpoints. The path mirror has a different shape
 * than /funding/{planId}/... so this proxy is its own file.
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
    ? [planId, "funding-plan", ...rest]
    : [planId, "funding-plan"];
  return proxyToApi(request, { pathPrefix: "plans", suffix });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const PUT = handle;
export const DELETE = handle;
export const OPTIONS = handle;
