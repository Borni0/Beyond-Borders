"use client";

import Link from "next/link";

/**
 * Global error boundary used by the App Router. Without this, Next 15's
 * build tries to fall back to the legacy pages-router error path, which
 * doesn't exist in App-Router-only projects.
 */
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-red-600">
            Error
          </p>
          <h1 className="mt-4 text-2xl font-semibold text-slate-900">
            Something went wrong
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            An unexpected error occurred. Please try again.
          </p>
          <div className="mt-6 flex justify-center gap-2">
            <button
              type="button"
              onClick={() => reset()}
              className="rounded-xl bg-teal-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-teal-700"
            >
              Try again
            </button>
            <Link
              href="/"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Back to home
            </Link>
          </div>
        </div>
      </body>
    </html>
  );
}
