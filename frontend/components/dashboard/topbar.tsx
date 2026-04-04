"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";

function headerCopy(pathname: string) {
  if (pathname.startsWith("/workspace")) {
    return {
      title: "Start a grading session",
      subtitle: "Upload the teacher answer key and begin the grading flow.",
    };
  }
  if (pathname.startsWith("/dashboard/")) {
    return {
      title: "Exam dashboard",
      subtitle: "Upload student PDFs, review scores, and inspect answers.",
    };
  }
  if (pathname.startsWith("/clusters/")) {
    return {
      title: "Answer clusters",
      subtitle: "Review grouped answer patterns for the selected question.",
    };
  }
  if (pathname.startsWith("/export/")) {
    return {
      title: "Export results",
      subtitle: "Download or review the final marks for this exam.",
    };
  }
  if (pathname.startsWith("/analytics/")) {
    return {
      title: "Analytics",
      subtitle: "View class performance and processing metrics.",
    };
  }
  return {
    title: "GradeSync",
    subtitle: "Simple grading workflow for teachers.",
  };
}

export function Topbar() {
  const pathname = usePathname();
  const { title, subtitle } = headerCopy(pathname);

  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/80 backdrop-blur-2xl">
      <div className="flex min-h-20 items-center gap-4 px-4 py-4 sm:px-6">
        <div className="min-w-0">
          <div className="text-lg font-semibold tracking-tight">{title}</div>
          <div className="text-sm text-muted-foreground">{subtitle}</div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {pathname !== "/workspace" ? (
            <Button asChild variant="secondary" size="sm">
              <Link href="/workspace">
                <ArrowLeft className="h-4 w-4" />
                New session
              </Link>
            </Button>
          ) : null}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
