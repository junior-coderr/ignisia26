"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BrainCircuit,
  FileOutput,
  FilePlus2,
  LayoutDashboard,
  Trash2,
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

  const [savedExams, setSavedExams] = useState<{exam_id: string, title: string, created_at: string, student_count: number}[]>([]);

  useEffect(() => {
    fetch("/api/exams")
      .then((res) => res.json())
      .then((data) => {
        if (data.exams) setSavedExams(data.exams);
      })
      .catch((err) => console.error(err));
  }, []);

  const deleteExam = async (examIdToDelete: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await fetch(`/api/exam/${examIdToDelete}`, { method: "DELETE" });
      setSavedExams((prev) => prev.filter((ex) => ex.exam_id !== examIdToDelete));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <aside className="hidden h-screen w-[260px] flex-col border-r border-[#e0e0e0] bg-[#f5f5f7] px-4 py-5 lg:flex">
      <Link href="/" className="mb-7 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-[8px] bg-black text-xs font-black text-white">
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
                  className="absolute inset-0 rounded-[8px] bg-[#0066cc]/10"
                  transition={{ type: "spring", stiffness: 300, damping: 28 }}
                />
              ) : null}
              <span
                className={cn(
                  "relative flex items-center gap-3 rounded-[8px] px-3 py-2.5 text-[14px] font-normal transition-all duration-150",
                  active ? "text-[#1d1d1f]" : "text-[#7a7a7a] hover:bg-[#e0e0e0]/30 hover:text-[#1d1d1f]",
                )}
              >
                <Icon className={cn("h-4 w-4", active && "text-primary")} />
                <span>{item.label}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-8 flex-1 overflow-y-auto pr-2 scrollbar-hide">
        <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Saved Keys
        </div>
        <div className="space-y-[2px]">
          {savedExams.map((exam) => {
            const isActive = examId === exam.exam_id;
            return (
              <Link 
                key={exam.exam_id} 
                href={`/dashboard/${exam.exam_id}`} 
                className="group relative flex items-center justify-between rounded-md px-3 py-2 transition-all hover:bg-muted/50"
              >
                {isActive && (
                  <motion.span
                    layoutId="saved-active"
                    className="absolute inset-0 rounded-md bg-primary/10 ring-1 ring-primary/20"
                    transition={{ type: "spring", stiffness: 300, damping: 28 }}
                  />
                )}
                <div className="relative z-10 flex flex-col overflow-hidden">
                  <span className={cn(
                    "truncate text-sm font-medium transition-colors",
                    isActive ? "text-primary" : "text-foreground group-hover:text-foreground"
                  )}>
                    {exam.title || "Reference Key"}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(exam.created_at || Date.now()).toLocaleDateString()} • {exam.student_count} students
                  </span>
                </div>
                <button
                  onClick={(e) => deleteExam(exam.exam_id, e)}
                  className="relative z-10 ml-2 rounded-md p-1.5 text-muted-foreground opacity-0 transition-all hover:bg-red-100 hover:text-red-600 group-hover:opacity-100"
                  title="Delete Exam"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </Link>
            );
          })}
          {savedExams.length === 0 && (
            <div className="px-3 py-2 text-xs text-muted-foreground">No saved keys yet.</div>
          )}
        </div>
      </div>

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
