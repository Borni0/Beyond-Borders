/**
 * Data source proxy: /api/sources/* → /api/v1/sources/*
 */
import { type NextRequest } from "next/server";

import { proxyToApi } from "@/lib/server-proxy";

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] | undefined }> },
) {
  const { path } = await context.params;
  return proxyToApi(request, { pathPrefix: "sources", suffix: path });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
