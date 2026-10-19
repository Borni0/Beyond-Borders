/**
 * Stress Test proxy: /api/stress-test/* → /api/v1/stress-test/*
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context?: { params?: Promise<{ path?: string[] | string | undefined }> },
) {
  const params = context?.params ? await context.params : {};
  const rawPath = params.path ?? [];
  const path = Array.isArray(rawPath)
    ? rawPath
    : typeof rawPath === "string"
      ? [rawPath]
      : [];
  return proxyToApi(request, { pathPrefix: "stress-test", suffix: path });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const PUT = handle;
export const DELETE = handle;
export const OPTIONS = handle;
