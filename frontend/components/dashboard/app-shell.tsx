import { Sidebar } from "@/components/dashboard/sidebar";
import { Topbar } from "@/components/dashboard/topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="relative flex">
        <Sidebar />
        <div className="min-h-screen flex-1">
          <Topbar />
          <main className="px-4 py-6 sm:px-6 xl:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
