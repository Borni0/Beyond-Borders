/**
 * Payments proxy: /api/payments/... → /api/v1/payments/...
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] | undefined }> },
) {
  const params = await context.params;
  const segments: string[] = params.path ?? [];
  const suffix: string[] = segments;
  return proxyToApi(request, { pathPrefix: "payments", suffix });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
