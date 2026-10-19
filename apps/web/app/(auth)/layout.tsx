import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-ivory px-4 py-12">
      <Link
        href="/"
        className="mb-8 flex items-center gap-2 text-lg font-semibold text-midnight"
      >
        <span aria-hidden="true" className="inline-block h-6 w-6 rounded-md bg-teal" />
        Beyond Borders
      </Link>
      {children}
    </main>
  );
}