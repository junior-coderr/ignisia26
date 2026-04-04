"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, ChevronDown, ChevronUp, TrendingDown, TrendingUp, Users } from "lucide-react";

import { ApiError, getExamClusters, getSummary } from "@/lib/api";
import type { ClusterGroup, ClustersResponse, SummaryResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Band config ──────────────────────────────────────────────────────────────

const BAND_CONFIG: Record<string, { color: string; bg: string; border: string; dot: string; label: string }> = {
  excellent: {
    label: "Excellent",
    color: "text-emerald-700 dark:text-emerald-300",
    bg: "bg-emerald-50 dark:bg-emerald-950/40",
    border: "border-emerald-200 dark:border-emerald-800",
    dot: "bg-emerald-500",
  },
  good: {
    label: "Good",
    color: "text-blue-700 dark:text-blue-300",
    bg: "bg-blue-50 dark:bg-blue-950/40",
    border: "border-blue-200 dark:border-blue-800",
    dot: "bg-blue-500",
  },
  average: {
    label: "Average",
    color: "text-amber-700 dark:text-amber-300",
    bg: "bg-amber-50 dark:bg-amber-950/40",
    border: "border-amber-200 dark:border-amber-800",
    dot: "bg-amber-500",
  },
  poor: {
    label: "Needs Improvement",
    color: "text-rose-700 dark:text-rose-300",
    bg: "bg-rose-50 dark:bg-rose-950/40",
    border: "border-rose-200 dark:border-rose-800",
    dot: "bg-rose-500",
  },
};

function getBandConfig(kind?: string) {
  return BAND_CONFIG[kind ?? ""] ?? BAND_CONFIG.poor;
}

// ── Score bar ────────────────────────────────────────────────────────────────

function ScoreBar({ ratio, dotClass }: { ratio: number; dotClass: string }) {
  return (
    <div className="mt-1 h-1.5 w-full rounded-full bg-muted">
      <div
        className={cn("h-full rounded-full transition-all", dotClass)}
        style={{ width: `${Math.round(Math.max(0, Math.min(1, ratio)) * 100)}%` }}
      />
    </div>
  );
}

// ── Student row ──────────────────────────────────────────────────────────────

function StudentRow({ student }: { student: ClusterGroup["students"][0] }) {
  const [open, setOpen] = useState(false);
  const pct = Math.round(student.score_ratio * 100);

  return (
    <div className="rounded-xl border border-border/60 bg-background">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-4 px-4 py-3 text-left"
      >
        {/* Name + roll */}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{student.name}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{student.roll_number}</div>
        </div>

        {/* Score pill */}
        <div className="shrink-0 text-right">
          <div className="text-sm font-semibold">{student.score}</div>
          <div className="text-xs text-muted-foreground">{pct}%</div>
        </div>

        {open ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
      </button>

      {open && (
        <div className="border-t border-border/60 px-4 pb-4 pt-3 space-y-3">
          {/* Answer text */}
          {student.answer_text && (
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Answer</div>
              <p className="text-sm leading-6 text-foreground/80 line-clamp-5">{student.answer_text}</p>
            </div>
          )}

          {/* Matched / missed */}
          <div className="grid gap-3 sm:grid-cols-2">
            {student.matched_concepts.length > 0 && (
              <div>
                <div className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                  <TrendingUp className="h-3 w-3" /> Got right
                </div>
                <div className="flex flex-wrap gap-1">
                  {student.matched_concepts.slice(0, 3).map((c) => (
                    <span key={c} className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {student.missed_concepts.length > 0 && (
              <div>
                <div className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-rose-600 dark:text-rose-400">
                  <TrendingDown className="h-3 w-3" /> Missed
                </div>
                <div className="flex flex-wrap gap-1">
                  {student.missed_concepts.slice(0, 3).map((c) => (
                    <span key={c} className="rounded-md bg-rose-100 px-2 py-0.5 text-xs text-rose-700 dark:bg-rose-950/60 dark:text-rose-300">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Band card ────────────────────────────────────────────────────────────────

function BandCard({ cluster }: { cluster: ClusterGroup }) {
  const [open, setOpen] = useState(false);
  const cfg = getBandConfig(cluster.cluster_kind);

  const topMissed: string[] = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of cluster.students)
      for (const c of s.missed_concepts)
        counts.set(c, (counts.get(c) ?? 0) + 1);
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([c]) => c);
  }, [cluster.students]);

  return (
    <div className={cn("rounded-2xl border p-5", cfg.bg, cfg.border)}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={cn("h-3 w-3 rounded-full shrink-0", cfg.dot)} />
          <div>
            <div className={cn("text-base font-semibold", cfg.color)}>{cfg.label}</div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              Avg score {cluster.avg_score.toFixed(1)} · {cluster.student_count} student{cluster.student_count !== 1 ? "s" : ""}
            </div>
          </div>
        </div>

        {/* Student count bubble */}
        <div className={cn("flex h-10 w-10 shrink-0 flex-col items-center justify-center rounded-full text-sm font-bold", cfg.dot, "text-white")}>
          {cluster.student_count}
        </div>
      </div>

      {/* Score bar */}
      <ScoreBar ratio={cluster.avg_score / 5} dotClass={cfg.dot} />

      {/* Insight line */}
      {cluster.teaching_recommendation && (
        <p className="mt-3 text-xs leading-5 text-muted-foreground">{cluster.teaching_recommendation}</p>
      )}

      {/* Top missed concepts */}
      {topMissed.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          <span className="text-xs text-muted-foreground mr-1">Missed:</span>
          {topMissed.map((c) => (
            <span key={c} className="rounded-md bg-rose-100 px-2 py-0.5 text-xs text-rose-700 dark:bg-rose-900/50 dark:text-rose-300">
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Expand students */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-4 flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        <Users className="h-3.5 w-3.5" />
        {open ? "Hide" : "Show"} students
        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {open && (
        <div className="mt-3 space-y-2">
          {cluster.students.map((s) => (
            <StudentRow key={s.roll_number} student={s} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function ClusterPage({ params }: { params: { examId: string } }) {
  const router = useRouter();
  const { examId } = params;

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [clusters, setClusters] = useState<ClustersResponse>({});
  const [questionId, setQuestionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [sum, clu] = await Promise.all([getSummary(examId), getExamClusters(examId)]);
        if (cancelled) return;
        setSummary(sum);
        setClusters(clu);
        const firstQ = sum.questions[0]?.q_number ?? Object.keys(clu)[0] ?? null;
        setQuestionId(firstQ);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/workspace");
          return;
        }
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [examId, router]);

  const activeClusters = useMemo(
    () => (questionId ? clusters[questionId] ?? [] : []),
    [clusters, questionId],
  );

  const selectedQuestion = useMemo(
    () => summary?.questions.find((q) => q.q_number === questionId) ?? null,
    [summary, questionId],
  );

  // total students across all bands for this question
  const totalAttempted = selectedQuestion?.students_attempted
    ?? activeClusters.reduce((s, c) => s + c.student_count, 0);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-sm text-muted-foreground">Loading clusters…</div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-border/70 bg-card hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-xl font-semibold">{summary?.title ?? "Cluster Analysis"}</h1>
          <p className="text-sm text-muted-foreground">Students grouped by performance band per question</p>
        </div>
      </div>

      {/* ── Question tabs ──────────────────────────────────────────── */}
      {summary?.questions && summary.questions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {summary.questions.map((q) => (
            <button
              key={q.q_number}
              type="button"
              onClick={() => setQuestionId(q.q_number)}
              className={cn(
                "rounded-lg border px-4 py-1.5 text-sm font-medium transition-all",
                questionId === q.q_number
                  ? "border-primary bg-primary text-primary-foreground shadow-sm"
                  : "border-border/70 bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground",
              )}
            >
              {q.q_number}
            </button>
          ))}
        </div>
      )}

      {/* ── Selected question summary ──────────────────────────────── */}
      {selectedQuestion && (
        <div className="rounded-2xl border border-border/70 bg-card px-5 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2 min-w-0">
              <BookOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
              <p className="truncate text-sm text-muted-foreground">{selectedQuestion.q_text}</p>
            </div>
            <div className="flex shrink-0 items-center gap-4 text-right text-sm">
              <div>
                <div className="font-semibold">{totalAttempted}</div>
                <div className="text-xs text-muted-foreground">attempted</div>
              </div>
              <div>
                <div className="font-semibold">{selectedQuestion.avg_score.toFixed(1)}</div>
                <div className="text-xs text-muted-foreground">avg score</div>
              </div>
              <div>
                <div className="font-semibold">{selectedQuestion.max_marks}</div>
                <div className="text-xs text-muted-foreground">max</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Band cards ─────────────────────────────────────────────── */}
      {activeClusters.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border/70 bg-card/60 p-10 text-center">
          <div className="text-2xl mb-2">📊</div>
          <p className="text-sm text-muted-foreground">
            No clusters yet for this question. Upload and grade student PDFs to see bands appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {activeClusters.map((cluster) => (
            <BandCard key={cluster.cluster_id} cluster={cluster} />
          ))}
        </div>
      )}
    </div>
  );
}
