/**
 * Decision Studio proxy: /api/decision-studio/{path} → /api/v1/decision-studio/{path}.
 *
 * Single catch-all that forwards ``compare`` and the ``comparisons``
 * CRUD endpoints. The backend uses 404 (not 403) on cross-tenant
 * access, so we just pass the response through verbatim.
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] | undefined }> },
) {
  const params = await context.params;
  const segments: string[] = params.path ?? [];
  return proxyToApi(request, {
    pathPrefix: "decision-studio",
    suffix: segments,
  });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const PUT = handle;
export const DELETE = handle;
export const OPTIONS = handle;