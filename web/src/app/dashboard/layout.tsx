export const dynamic = "force-dynamic";

import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNav } from "@/components/layout/TopBar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 pb-16 md:pb-0">{children}</main>
      <MobileNav />
    </div>
  );
}
