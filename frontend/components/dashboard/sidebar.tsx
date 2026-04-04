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
    <aside className="hidden h-screen w-[276px] flex-col border-r border-border/70 bg-card/70 px-5 py-6 backdrop-blur-2xl lg:flex">
      <Link href="/" className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#2563eb,#22d3ee)] text-sm font-black text-white shadow-glow">
          GS
        </div>
        <div>
          <div className="text-sm font-semibold text-muted-foreground">Teacher Grading</div>
          <div className="text-xl font-semibold tracking-tight">GradeSync</div>
        </div>
      </Link>

      <nav className="space-y-1.5">
        {items.map((item, index) => {
          const href = item.href(examId);
          const active = pathname === href;
          const Icon = item.icon;
          return (
            <Link key={item.label} href={href} className="relative block">
              {active ? (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-2xl bg-primary/10 ring-1 ring-primary/20"
                  transition={{ type: "spring", stiffness: 260, damping: 26 }}
                />
              ) : null}
              <span
                className={cn(
                  "relative flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition-all",
                  active ? "text-foreground" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
                style={{ transitionDelay: `${index * 14}ms` }}
              >
                <Icon className={cn("h-4 w-4", active && "text-primary")} />
                <span>{item.label}</span>
              </span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
