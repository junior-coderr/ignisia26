"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BrainCircuit,
  FileOutput,
  FilePlus2,
  LayoutDashboard,
} from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

const items = [
  { label: "New Session", icon: FilePlus2, href: () => "/workspace" },
  { label: "Dashboard", icon: LayoutDashboard, href: (examId?: string) => (examId ? `/dashboard/${examId}` : "/workspace") },
  { label: "Clusters", icon: BrainCircuit, href: (examId?: string) => (examId ? `/clusters/${examId}` : "/workspace") },
  { label: "Export", icon: FileOutput, href: (examId?: string) => (examId ? `/export/${examId}` : "/workspace") },
];

function inferExamId(pathname: string) {
  const match = pathname.match(/\/(?:dashboard|clusters|analytics|export)\/([^/]+)/);
  return match?.[1];
}

export function Sidebar() {
  const pathname = usePathname();
  const examId = inferExamId(pathname);

  return (
    <aside className="hidden h-screen w-[260px] flex-col border-r border-border/50 bg-card/60 px-4 py-5 backdrop-blur-2xl lg:flex">
      <Link href="/" className="mb-7 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-xs font-black text-white">
          GS
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">AI Grading</div>
          <div className="text-lg font-semibold tracking-tight leading-tight">GradeSync</div>
        </div>
      </Link>

      <nav className="space-y-1">
        {items.map((item) => {
          const href = item.href(examId);
          const active = pathname === href;
          const Icon = item.icon;
          return (
            <Link key={item.label} href={href} className="relative block">
              {active ? (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-xl bg-primary/8 ring-1 ring-primary/15"
                  transition={{ type: "spring", stiffness: 300, damping: 28 }}
                />
              ) : null}
              <span
                className={cn(
                  "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-150",
                  active ? "text-foreground" : "text-muted-foreground hover:bg-muted/40 hover:text-foreground",
                )}
              >
                <Icon className={cn("h-4 w-4", active && "text-primary")} />
                <span>{item.label}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="mt-auto px-2 pt-4">
        <div className="rounded-xl border border-border/40 bg-muted/30 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Session</div>
          <div className="mt-1 truncate text-xs text-muted-foreground/80">
            {examId ? `Exam ${examId.slice(0, 8)}…` : "No active session"}
          </div>
        </div>
      </div>
    </aside>
  );
}
