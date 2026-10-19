/**
 * Route protection.
 *
 * The dashboard pages also call `requireUser()` server-side, which is the
 * authoritative check. Middleware is a fast pre-filter that redirects to
 * the sign-in page so the user lands somewhere sensible.
 */

import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = new Set<string>([
  "/",
  "/sign-in",
  "/sign-up",
  "/forgot-password",
]);

function isPublic(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true;
  if (pathname.startsWith("/api/auth/")) return true;
  if (pathname.startsWith("/_next/")) return true;
  if (pathname === "/favicon.ico" || pathname === "/robots.txt") return true;
  return false;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  // The session cookie is the source of truth. The server-side requireUser()
  // dependency will re-verify on every protected request; here we just check
  // that a cookie was sent at all so the browser sees a redirect immediately.
  const hasSession = request.cookies.has("bb_session");
  if (!hasSession) {
    const next = encodeURIComponent(pathname + (search ?? ""));
    const url = request.nextUrl.clone();
    url.pathname = "/sign-in";
    url.search = `?next=${next}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};