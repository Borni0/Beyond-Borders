"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { MOBILE_NAV_ITEMS } from "./nav-items";

export function MobileNav() {
  const pathname = usePathname() ?? "/";

  return (
    <nav
      aria-label="Mobile primary"
      className="fixed inset-x-0 bottom-0 z-10 flex justify-around border-t border-border bg-white px-2 py-2 md:hidden"
    >
      {MOBILE_NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive =
          item.href === "/dashboard"
            ? pathname === "/dashboard"
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex flex-col items-center justify-center rounded-lg px-3 py-2 text-[11px]",
              isActive ? "text-teal" : "text-slate",
            )}
          >
            <Icon className="mb-1 h-5 w-5" aria-hidden="true" />
            <span className="line-clamp-1">{item.label.split(" ")[0]}</span>
          </Link>
        );
      })}
    </nav>
  );
}