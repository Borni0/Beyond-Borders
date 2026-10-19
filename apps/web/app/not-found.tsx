import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-teal-600">
          404
        </p>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900">
          Page not found
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          The page you were looking for doesn’t exist or may have moved.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center justify-center rounded-xl bg-teal-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-teal-700"
        >
          Back to home
        </Link>
      </div>
    </main>
  );
}
