/**
 * Auth helpers for server components and route handlers.
 */

import { redirect } from "next/navigation";

import { getCurrentUser } from "./api";
import type { User } from "@beyond-borders/shared-types";

/** Get the current user, redirecting to /sign-in if absent. */
export async function requireUser(nextPath?: string): Promise<User> {
  const user = await getCurrentUser();
  if (!user) {
    const next = nextPath ? `?next=${encodeURIComponent(nextPath)}` : "";
    redirect(`/sign-in${next}`);
  }
  return user;
}
