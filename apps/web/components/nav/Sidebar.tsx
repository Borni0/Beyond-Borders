"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav-items";

export function Sidebar() {
  const pathname = usePathname() ?? "/";

  return (
    <nav
      aria-label="Primary"
      className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-border md:bg-white"
    >
      <div className="px-6 py-6">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 text-lg font-semibold text-midnight"
        >
          <span aria-hidden="true" className="inline-block h-6 w-6 rounded-md bg-teal" />
          Beyond Borders
        </Link>
        <p className="mt-1 text-xs text-slate">Financial clarity before commitment.</p>
      </div>
      <ul className="flex flex-1 flex-col gap-1 px-3 pb-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-mint text-midnight"
                    : "text-slate hover:bg-ivory hover:text-midnight",
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{item.label}</span>
                {item.phase > 1 ? (
                  <span
                    aria-label={`Coming in phase ${item.phase}`}
                    className="ml-auto rounded-full bg-ivory px-2 py-0.5 text-[10px] uppercase text-slate"
                  >
                    Phase {item.phase}
                  </span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="px-6 py-4 text-xs text-slate">
        <p>All tools available</p>
      </div>
    </nav>
  );
}