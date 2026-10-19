/**
 * Readiness proxy: /api/readiness/{planId} → /api/v1/plans/{planId}/readiness
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context: { params: Promise<{ planId: string }> },
) {
  const { planId } = await context.params;
  return proxyToApi(request, {
    pathPrefix: "plans",
    suffix: [planId, "readiness"],
  });
}

export const GET = handle;
export const OPTIONS = handle;
