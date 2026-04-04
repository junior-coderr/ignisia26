"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, BarChart3, Cpu, TimerReset } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getExamMetrics, getResults, getSummary } from "@/lib/api";
import type { ExamMetricsWrapper, ResultsResponse, SummaryResponse } from "@/lib/types";

const chartColors = ["#2563eb", "#22d3ee", "#10b981", "#f59e0b", "#f43f5e"];

export default function AnalyticsPage({ params }: { params: { examId: string } }) {
  const router = useRouter();
  const examId = params.examId;
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [metrics, setMetrics] = useState<ExamMetricsWrapper | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [summaryResponse, resultsResponse, metricsResponse] = await Promise.all([
          getSummary(examId),
          getResults(examId),
          getExamMetrics(examId),
        ]);
        if (cancelled) return;
        setSummary(summaryResponse);
        setResults(resultsResponse);
        setMetrics(metricsResponse);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          router.replace("/workspace");
          return;
        }
        throw error;
      }
    }
    load().catch(console.error);
    return () => {
      cancelled = true;
    };
  }, [examId, router]);

  const gradeDistribution = useMemo(() => {
    const counts = { correct: 0, partial: 0, formula_half_credit: 0, incorrect: 0 };
    results?.students.forEach((student) => {
      Object.values(student.scores).forEach((score) => {
        const band = score.grade_band as keyof typeof counts;
        if (band in counts) counts[band] += 1;
      });
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [results]);

  const questionPerformance = useMemo(
    () =>
      summary?.questions.map((question) => ({
        name: question.q_number,
        average: question.avg_score,
        similarity: question.avg_similarity * 100,
      })) ?? [],
    [summary],
  );

  const timings = useMemo(
    () =>
      Object.entries(metrics?.metrics.timings ?? {}).map(([name, value]) => ({
        name: name.replace("_seconds", ""),
        seconds: value,
      })),
    [metrics],
  );

  return (
    <div className="space-y-6">
      <section className="section-grid">
        <Card className="p-8">
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="info">Analytics layer</Badge>
            <Badge variant="neutral">Performance + grading quality</Badge>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight">A class-level view of accuracy, workload reduction, and pipeline cost.</h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
            This dashboard combines grading outputs with pipeline telemetry so professors can assess both student
            performance and the efficiency gains from AI-assisted clustering.
          </p>

          <div className="mt-8 grid gap-4 xl:grid-cols-4">
            <StatCard
              label="Class average"
              value={`${summary?.class_average || 0}/${summary?.max_total || 0}`}
              detail="Average score across all uploaded students"
              icon={<BarChart3 className="h-5 w-5" />}
            />
            <StatCard
              label="LLM reviews used"
              value={`${metrics?.metrics.llm_reviews_used || 0}`}
              detail="Escalated answers routed for secondary judgment"
              icon={<Cpu className="h-5 w-5" />}
            />
            <StatCard
              label="Review candidates"
              value={`${metrics?.metrics.llm_review_candidates || 0}`}
              detail="Low-confidence or contradictory answers flagged for extra review"
              icon={<Activity className="h-5 w-5" />}
            />
            <StatCard
              label="Total runtime"
              value={`${(metrics?.metrics.timings.reference_seconds || 0) + (metrics?.metrics.timings.student_seconds || 0)}s`}
              detail="Reference prep plus student processing"
              icon={<TimerReset className="h-5 w-5" />}
            />
          </div>
        </Card>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="p-6">
          <div className="mb-4">
            <div className="text-lg font-semibold">Question-wise performance</div>
            <div className="text-sm text-muted-foreground">Average marks for each question.</div>
          </div>
          <div className="h-[360px]">
            {!questionPerformance.length ? (
              <Skeleton className="h-full rounded-[28px]" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={questionPerformance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                  <XAxis dataKey="name" stroke="currentColor" opacity={0.4} />
                  <YAxis stroke="currentColor" opacity={0.4} />
                  <Tooltip />
                  <Bar dataKey="average" radius={[10, 10, 0, 0]} fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-4">
            <div className="text-lg font-semibold">Grade band distribution</div>
            <div className="text-sm text-muted-foreground">How the evaluated answer set breaks down across correctness bands.</div>
          </div>
          <div className="h-[360px]">
            {!gradeDistribution.length ? (
              <Skeleton className="h-full rounded-[28px]" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={gradeDistribution} dataKey="value" nameKey="name" innerRadius={72} outerRadius={122} paddingAngle={5}>
                    {gradeDistribution.map((entry, index) => (
                      <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <div className="mb-4">
          <div className="text-lg font-semibold">Pipeline timings</div>
          <div className="text-sm text-muted-foreground">Operational timing for OCR, embeddings, rubric creation, review, and clustering.</div>
        </div>
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-7">
          {timings.length
            ? timings.map((timing, index) => (
                <div key={timing.name} className="rounded-2xl border border-border/70 bg-background/70 p-4">
                  <div className="metric-label mb-2">{timing.name}</div>
                  <div className="text-2xl font-semibold" style={{ color: chartColors[index % chartColors.length] }}>
                    {timing.seconds.toFixed(2)}s
                  </div>
                </div>
              ))
            : Array.from({ length: 7 }).map((_, index) => <Skeleton key={index} className="h-24 rounded-2xl" />)}
        </div>
      </Card>
    </div>
  );
}
