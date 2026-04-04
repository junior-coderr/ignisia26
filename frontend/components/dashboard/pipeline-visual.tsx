"use client";

import { motion } from "framer-motion";
import { BrainCircuit, FileScan, GitBranch, Layers3, ScanText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const pipeline = [
  { key: "ocr", label: "OCR", icon: FileScan, blurb: "Handwriting to structured text" },
  { key: "segmentation", label: "Segmentation", icon: ScanText, blurb: "Question-aware extraction" },
  { key: "embeddings", label: "Embeddings", icon: Layers3, blurb: "Multilingual semantic vectors" },
  { key: "matching", label: "Matching", icon: BrainCircuit, blurb: "Rubric and evidence scoring" },
  { key: "clusters", label: "Clustering", icon: GitBranch, blurb: "Reasoning-family discovery" },
];

export function PipelineVisual({
  activeStage,
}: {
  activeStage: string;
}) {
  const activeIndex = Math.max(0, pipeline.findIndex((stage) => stage.key === activeStage));

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-border/70 bg-card/70 p-6">
      <div className="absolute inset-x-6 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-primary/0 via-primary/30 to-primary/0" />
      <div className="grid gap-4 md:grid-cols-5">
        {pipeline.map((stage, index) => {
          const Icon = stage.icon;
          const state =
            index < activeIndex ? "complete" : index === activeIndex ? "active" : "idle";
          return (
            <motion.div
              key={stage.key}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
              className="relative"
            >
              <div
                className={cn(
                  "relative rounded-3xl border p-5 transition-all",
                  state === "active" && "border-primary/35 bg-primary/10 shadow-glow",
                  state === "complete" && "border-emerald-500/20 bg-emerald-500/10",
                  state === "idle" && "border-border/70 bg-background/70",
                )}
              >
                <div className="mb-4 flex items-center justify-between">
                  <div
                    className={cn(
                      "flex h-11 w-11 items-center justify-center rounded-2xl",
                      state === "active" && "bg-primary text-primary-foreground",
                      state === "complete" && "bg-emerald-500 text-white",
                      state === "idle" && "bg-muted text-muted-foreground",
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <Badge
                    variant={
                      state === "active" ? "info" : state === "complete" ? "success" : "neutral"
                    }
                  >
                    {state === "active" ? "Live" : state === "complete" ? "Done" : "Queued"}
                  </Badge>
                </div>
                <div className="text-base font-semibold">{stage.label}</div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{stage.blurb}</p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
