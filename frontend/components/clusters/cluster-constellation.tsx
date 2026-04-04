"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Calculator, CheckCircle2, CircleDot, Users2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ClusterGroup } from "@/lib/types";
import { cn, formatGradeBand } from "@/lib/utils";

function toneForBand(gradeBand: string) {
  if (gradeBand === "correct" || gradeBand === "excellent") {
    return {
      badge: "success" as const,
      bar: "bg-emerald-500",
      chip: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-300",
      panel: "from-emerald-500/16 via-emerald-500/6 to-transparent",
      border: "border-emerald-500/25",
      icon: CheckCircle2,
    };
  }

  if (gradeBand === "formula_half_credit" || gradeBand === "good") {
    return {
      badge: "info" as const,
      bar: "bg-blue-500",
      chip: "bg-blue-500/12 text-blue-600 dark:text-blue-300",
      panel: "from-blue-500/18 via-blue-500/6 to-transparent",
      border: "border-blue-500/25",
      icon: CheckCircle2,
    };
  }

  if (gradeBand === "partial" || gradeBand === "average") {
    return {
      badge: "warning" as const,
      bar: "bg-amber-500",
      chip: "bg-amber-500/12 text-amber-600 dark:text-amber-300",
      panel: "from-amber-500/18 via-amber-500/6 to-transparent",
      border: "border-amber-500/25",
      icon: CircleDot,
    };
  }

  return {
    badge: "danger" as const,
    bar: "bg-rose-500",
    chip: "bg-rose-500/12 text-rose-600 dark:text-rose-300",
    panel: "from-rose-500/18 via-rose-500/6 to-transparent",
    border: "border-rose-500/25",
    icon: AlertTriangle,
  };
}

function compactLabel(label: string) {
  return label
    .replace("Correct Concept Cluster:", "Shared correct reasoning:")
    .replace("Partial Reasoning Cluster:", "Partial answers:")
    .trim();
}

export function ClusterConstellation({
  clusters,
  selectedClusterId,
  onSelect,
  questionLabel,
  totalStudents,
}: {
  clusters: ClusterGroup[];
  selectedClusterId?: string;
  onSelect: (clusterId: string) => void;
  questionLabel?: string;
  totalStudents?: number;
}) {
  const attemptBase = Math.max(totalStudents || 0, clusters.reduce((sum, cluster) => sum + cluster.student_count, 0), 1);

  return (
    <div className="overflow-hidden rounded-[32px] border border-border/70 bg-card/80 p-6 shadow-panel backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          <div className="metric-label">Visual Cluster Map</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight">
            {questionLabel ? `${questionLabel} answer groups` : "Answer groups"}
          </h2>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            Each block is one recurring reasoning pattern. Bigger bars mean more students. Color tells you whether the
            group is mostly correct, partial, arithmetic-only, or misconception-heavy.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="success">Excellent</Badge>
          <Badge variant="info">Good</Badge>
          <Badge variant="warning">Average</Badge>
          <Badge variant="danger">Needs Improvement</Badge>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {!clusters.length ? (
          <div className="rounded-[28px] border border-dashed border-border/70 bg-background/60 p-8 text-center text-sm leading-7 text-muted-foreground lg:col-span-2">
            No cluster groups are ready for this question yet. Once the backend finishes grading, the answer families
            will appear here.
          </div>
        ) : null}

        {clusters.map((cluster, index) => {
          const tone = toneForBand(cluster.cluster_kind || cluster.grade_band);
          const share = Math.max(8, Math.round((cluster.student_count / attemptBase) * 100));
          const active = selectedClusterId === cluster.cluster_id;
          const Icon = tone.icon;

          return (
            <motion.button
              key={cluster.cluster_id}
              type="button"
              onClick={() => onSelect(cluster.cluster_id)}
              whileHover={{ y: -3 }}
              transition={{ duration: 0.18 }}
              className={cn(
                "relative overflow-hidden rounded-[30px] border bg-gradient-to-br p-5 text-left transition-all",
                active
                  ? `${tone.border} ${tone.panel} shadow-[0_18px_60px_rgba(15,23,42,0.12)]`
                  : "border-border/70 from-background via-background to-muted/35 hover:border-primary/20",
              )}
            >
              <div className={cn("absolute inset-x-0 top-0 h-1.5", tone.bar)} />
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="metric-label">Cluster {index + 1}</div>
                  <h3 className="mt-2 text-lg font-semibold leading-6">{compactLabel(cluster.label)}</h3>
                </div>
                <Badge variant={tone.badge}>{formatGradeBand(cluster.grade_band)}</Badge>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-[auto,1fr]">
                <div className={cn("flex h-16 w-16 flex-col items-center justify-center rounded-[24px]", tone.chip)}>
                  <Icon className="h-5 w-5" />
                  <div className="mt-1 text-lg font-semibold">{cluster.student_count}</div>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-sm font-medium">
                      <span>Share of attempts</span>
                      <span>{Math.round((cluster.student_count / attemptBase) * 100)}%</span>
                    </div>
                    <div className="mt-2 h-2.5 rounded-full bg-muted">
                      <div className={cn("h-full rounded-full transition-all", tone.bar)} style={{ width: `${share}%` }} />
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl border border-border/70 bg-background/70 p-3">
                      <div className="metric-label mb-1">Avg marks</div>
                      <div className="text-lg font-semibold">{cluster.avg_score.toFixed(1)}</div>
                    </div>
                    <div className="rounded-2xl border border-border/70 bg-background/70 p-3">
                      <div className="metric-label mb-1">Alignment</div>
                      <div className="text-lg font-semibold">{Math.round(cluster.avg_similarity * 100)}%</div>
                    </div>
                    <div className="rounded-2xl border border-border/70 bg-background/70 p-3">
                      <div className="metric-label mb-1">Confidence</div>
                      <div className="text-lg font-semibold">{Math.round(cluster.avg_confidence * 100)}%</div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="mt-4 line-clamp-2 text-sm leading-7 text-muted-foreground">{cluster.common_pattern}</p>

              <div className="mt-4 flex items-center justify-between text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                <span>{cluster.is_outlier ? "Unique answers" : "Recurring pattern"}</span>
                <Users2 className="h-4 w-4" />
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
