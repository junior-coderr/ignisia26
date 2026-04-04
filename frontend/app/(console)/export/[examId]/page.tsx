"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, exportCsvUrl, getResults } from "@/lib/api";
import type { ResultsResponse } from "@/lib/types";

export default function ExportPage({ params }: { params: { examId: string } }) {
  const router = useRouter();
  const examId = params.examId;
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getResults(examId)
      .then(setResults)
      .catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          router.replace("/workspace");
          return;
        }
        console.error(error);
      });
  }, [examId, router]);

  const filteredStudents = useMemo(() => {
    if (!results) return [];
    const query = search.trim().toLowerCase();
    if (!query) return results.students;
    return results.students.filter((student) => {
      return (
        student.name.toLowerCase().includes(query) ||
        student.roll_number.toLowerCase().includes(query) ||
        student.exam_code.toLowerCase().includes(query)
      );
    });
  }, [results, search]);

  return (
    <div className="space-y-6">
      <Card className="p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="metric-label mb-2">Export center</div>
            <h1 className="text-4xl font-semibold tracking-tight">Download or inspect student-level results.</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
              Export a clean CSV for record-keeping or scan the totals and per-question marks directly inside the dashboard.
            </p>
          </div>
          <Button asChild size="lg">
            <a href={exportCsvUrl(examId)}>
              <Download className="h-4 w-4" />
              Download CSV
            </a>
          </Button>
        </div>
      </Card>

      <Card className="p-6">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-lg font-semibold">Results table</div>
            <div className="text-sm text-muted-foreground">Search by student name, roll number, or exam code.</div>
          </div>
          <div className="relative max-w-md md:w-[320px]">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input className="pl-10" placeholder="Search students..." value={search} onChange={(event) => setSearch(event.target.value)} />
          </div>
        </div>

        <div className="overflow-hidden rounded-[28px] border border-border/70">
          <div className="grid grid-cols-[1.2fr,0.9fr,0.8fr] bg-muted/60 px-5 py-3 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
            <span>Student</span>
            <span>Exam code</span>
            <span>Total</span>
          </div>
          <div className="divide-y divide-border/70">
            {!results
              ? Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="m-4 h-16 rounded-2xl" />)
              : filteredStudents.map((student) => (
                  <div key={student.roll_number} className="grid grid-cols-[1.2fr,0.9fr,0.8fr] items-center px-5 py-4">
                    <div>
                      <div className="font-semibold">{student.name}</div>
                      <div className="text-sm text-muted-foreground">{student.roll_number}</div>
                    </div>
                    <div className="text-sm text-muted-foreground">{student.exam_code || "N/A"}</div>
                    <div className="text-lg font-semibold">
                      {student.total.toFixed(1)} / {results.max_total}
                    </div>
                  </div>
                ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
