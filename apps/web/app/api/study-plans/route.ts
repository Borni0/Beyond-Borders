/**
 * Study plan root proxy: /api/study-plans -> /api/v1/study-plans
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context?: { params?: Promise<Record<string, string | string[] | undefined>> },
) {
  const params = context?.params ? await context.params : {};
  const rawPath = params.path ?? [];
  const path = Array.isArray(rawPath)
    ? rawPath
    : typeof rawPath === "string"
      ? [rawPath]
      : [];
  return proxyToApi(request, { pathPrefix: "study-plans", suffix: path });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
