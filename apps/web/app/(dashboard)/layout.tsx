import { MobileNav } from "@/components/nav/MobileNav";
import { Sidebar } from "@/components/nav/Sidebar";
import { requireUser } from "@/lib/auth";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Authoritative auth check (middleware is just a fast pre-filter).
  await requireUser();

  return (
    <div className="flex min-h-screen flex-col bg-ivory">
      <div className="flex flex-1">
        <Sidebar />
        <div className="flex flex-1 flex-col">
          <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8 pb-24 md:pb-8">
            {children}
          </main>
          <MobileNav />
        </div>
      </div>
    </div>
  );
}