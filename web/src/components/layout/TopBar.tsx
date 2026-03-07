"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Users, BookOpen, BarChart3, Settings } from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/dashboard/grove", label: "Grove", icon: Users },
  { href: "/dashboard/plan", label: "Plan", icon: BookOpen },
  { href: "/dashboard/insights", label: "Insights", icon: BarChart3 },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-card border-t flex justify-around py-2">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-col items-center gap-1 px-2 py-1 text-xs",
              active ? "text-primary" : "text-muted-foreground"
            )}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
