"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Users, BookOpen, BarChart3, Settings, LogOut } from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/grove", label: "My Grove", icon: Users },
  { href: "/dashboard/plan", label: "Study Plan", icon: BookOpen },
  { href: "/dashboard/insights", label: "Insights", icon: BarChart3 },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { displayName, signOut } = useAuth();
  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <aside className="hidden md:flex flex-col w-64 border-r bg-card h-screen sticky top-0">
      <div className="p-6 border-b">
        <Link href="/dashboard" className="flex items-center gap-2">
          <span className="text-2xl">🍄</span>
          <span className="text-xl font-bold">Enoki</span>
        </Link>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t">
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">{initials || "?"}</AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium truncate flex-1">{displayName}</span>
          <Button variant="ghost" size="icon" onClick={signOut} title="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
