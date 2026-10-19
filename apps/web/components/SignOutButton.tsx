"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";

export function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignOut() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/logout", { method: "POST" });
      if (!res.ok && res.status !== 204) {
        const body = (await res.json().catch(() => null)) as
          | { error?: { message?: string } }
          | null;
        throw new Error(body?.error?.message ?? "Sign-out failed.");
      }
      router.replace("/sign-in");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-out failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <Button variant="secondary" onClick={handleSignOut} isLoading={loading}>
        Sign out
      </Button>
      {error ? (
        <p role="alert" className="text-xs text-red">
          {error}
        </p>
      ) : null}
    </div>
  );
}