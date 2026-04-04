"use client";

import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { FilePlus2, FileText, UploadCloud, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function UploadDropzone({
  title,
  subtitle,
  files,
  onFilesChange,
  multiple = false,
}: {
  title: string;
  subtitle: string;
  files: File[];
  onFilesChange: (files: File[]) => void;
  multiple?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function addFiles(incoming: FileList | null) {
    if (!incoming?.length) return;
    const list = Array.from(incoming);
    onFilesChange(multiple ? [...files, ...list] : [list[0]]);
  }

  return (
    <div className="space-y-4">
      <motion.button
        type="button"
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.995 }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          addFiles(event.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "group relative flex min-h-[220px] w-full flex-col items-center justify-center overflow-hidden rounded-[28px] border border-dashed px-8 py-12 text-center transition-all",
          isDragging
            ? "border-primary bg-primary/10 shadow-glow"
            : "border-border/70 bg-card/70 hover:border-primary/40 hover:bg-card",
        )}
      >
        <div className="absolute inset-0 bg-hero-grid bg-[size:28px_28px] opacity-[0.06]" />
        <div className="absolute -left-10 top-10 h-24 w-24 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute bottom-10 right-0 h-28 w-28 rounded-full bg-cyan-400/15 blur-3xl" />

        <div className="relative flex h-16 w-16 items-center justify-center rounded-3xl bg-[linear-gradient(135deg,#2563eb,#22d3ee)] text-white shadow-glow">
          {multiple ? <UploadCloud className="h-7 w-7" /> : <FilePlus2 className="h-7 w-7" />}
        </div>
        <div className="relative mt-6 space-y-2">
          <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
          <p className="max-w-xl text-sm leading-6 text-muted-foreground">{subtitle}</p>
        </div>
        <div className="relative mt-5 flex flex-wrap items-center justify-center gap-2">
          <Badge variant="info">PDF</Badge>
          <Badge variant="neutral">Structured OCR</Badge>
          <Badge variant="neutral">Question-linked extraction</Badge>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,image/*"
          multiple={multiple}
          className="hidden"
          onChange={(event) => addFiles(event.target.files)}
        />
      </motion.button>

      {files.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {files.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center gap-3 rounded-2xl border border-border/70 bg-card/70 px-4 py-3"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <FileText className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{file.name}</div>
                <div className="text-xs text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>
              <Button
                size="icon"
                variant="ghost"
                onClick={(event) => {
                  event.stopPropagation();
                  onFilesChange(files.filter((_, fileIndex) => fileIndex !== index));
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
