import { AppShell } from "@/components/dashboard/app-shell";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
