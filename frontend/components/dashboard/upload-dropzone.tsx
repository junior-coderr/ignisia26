"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FilePlus2, FileText, UploadCloud, X, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

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
    <div className="space-y-3">
      <motion.button
        type="button"
        whileHover={{ scale: 1.005 }}
        whileTap={{ scale: 0.998 }}
        onDragOver={(event: React.DragEvent) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event: React.DragEvent) => {
          event.preventDefault();
          setIsDragging(false);
          addFiles(event.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "group relative flex w-full flex-col items-center justify-center overflow-hidden rounded-2xl border border-dashed px-8 py-10 text-center transition-all duration-300",
          isDragging
            ? "border-primary/60 bg-primary/8 shadow-[0_0_0_2px_rgba(37,99,235,0.12)]"
            : files.length > 0
              ? "border-success/40 bg-success/4"
              : "border-border/60 bg-card/50 hover:border-primary/30 hover:bg-card/70",
        )}
      >
        {/* Subtle grid background */}
        <div className="absolute inset-0 bg-hero-grid bg-[size:20px_20px] opacity-[0.04]" />

        <div className={cn(
          "relative flex h-12 w-12 items-center justify-center rounded-2xl transition-all duration-300",
          files.length > 0
            ? "bg-success/15 text-success"
            : "bg-primary/10 text-primary group-hover:bg-primary/15",
        )}>
          {files.length > 0 ? (
            <CheckCircle2 className="h-6 w-6" />
          ) : multiple ? (
            <UploadCloud className="h-6 w-6" />
          ) : (
            <FilePlus2 className="h-6 w-6" />
          )}
        </div>

        <div className="relative mt-4 space-y-1">
          <h3 className="text-base font-medium tracking-tight">
            {files.length > 0
              ? `${files.length} file${files.length > 1 ? "s" : ""} selected`
              : title}
          </h3>
          <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
            {files.length > 0
              ? "Click to add more or drag additional files"
              : subtitle}
          </p>
        </div>

        <div className="relative mt-4 flex flex-wrap items-center justify-center gap-2">
          <Badge variant="info">PDF</Badge>
          <Badge variant="neutral">Images</Badge>
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

      {/* File list */}
      <AnimatePresence mode="popLayout">
        {files.map((file, index) => (
          <motion.div
            key={`${file.name}-${file.size}`}
            initial={{ opacity: 0, height: 0, y: -8 }}
            animate={{ opacity: 1, height: "auto", y: 0 }}
            exit={{ opacity: 0, height: 0, y: -8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card/60 px-4 py-2.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/8 text-primary">
                <FileText className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{file.name}</div>
                <div className="text-xs text-muted-foreground">{formatSize(file.size)}</div>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8 shrink-0 rounded-lg"
                onClick={(event) => {
                  event.stopPropagation();
                  onFilesChange(files.filter((_, fileIndex) => fileIndex !== index));
                }}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
