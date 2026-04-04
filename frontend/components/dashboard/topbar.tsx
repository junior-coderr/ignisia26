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
      subtitle: "Upload the teacher answer key to begin.",
    };
  }
  if (pathname.startsWith("/dashboard/")) {
    return {
      title: "Exam dashboard",
      subtitle: "Upload student PDFs, review scores, inspect answers.",
    };
  }
  if (pathname.startsWith("/clusters/")) {
    return {
      title: "Answer clusters",
      subtitle: "Student groups by performance band.",
    };
  }
  if (pathname.startsWith("/export/")) {
    return {
      title: "Export results",
      subtitle: "Download final marks for this exam.",
    };
  }
  return {
    title: "GradeSync",
    subtitle: "AI-powered grading workflow.",
  };
}

export function Topbar() {
  const pathname = usePathname();
  const { title, subtitle } = headerCopy(pathname);

  return (
    <header className="sticky top-0 z-30 border-b border-border/50 bg-background/85 backdrop-blur-2xl">
      <div className="flex h-16 items-center gap-4 px-5">
        <div className="min-w-0">
          <div className="text-[15px] font-semibold tracking-tight">{title}</div>
          <div className="text-xs text-muted-foreground">{subtitle}</div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {pathname !== "/workspace" ? (
            <Button asChild variant="ghost" size="sm">
              <Link href="/workspace">
                <ArrowLeft className="h-3.5 w-3.5" />
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
