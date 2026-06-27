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
          "group relative flex w-full flex-col items-center justify-center overflow-hidden rounded-[18px] border border-dashed px-8 py-10 text-center transition-all duration-300",
          isDragging
            ? "border-[#0066cc] bg-[#0066cc]/5 shadow-[0_0_0_2px_rgba(0,102,204,0.15)]"
            : files.length > 0
              ? "border-[#00b259]/40 bg-[#00b259]/5"
              : "border-[#e0e0e0] bg-white hover:border-[#0066cc]/40 hover:bg-[#fafafc]",
        )}
      >
        <div className={cn(
          "relative flex h-12 w-12 items-center justify-center rounded-[11px] transition-all duration-300",
          files.length > 0
            ? "bg-[#00b259]/15 text-[#00b259]"
            : "bg-[#f5f5f7] text-[#0066cc] group-hover:bg-[#0066cc]/10",
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
          <h3 className="text-[17px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
            {files.length > 0
              ? `${files.length} file${files.length > 1 ? "s" : ""} selected`
              : title}
          </h3>
          <p className="max-w-md text-[14px] leading-[1.43] text-[#7a7a7a]">
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
            <div className="flex items-center gap-3 rounded-[11px] border border-[#e0e0e0] bg-white px-4 py-2.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] bg-[#f5f5f7] text-[#0066cc]">
                <FileText className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[14px] font-semibold text-[#1d1d1f]">{file.name}</div>
                <div className="text-[12px] text-[#7a7a7a]">{formatSize(file.size)}</div>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8 shrink-0 rounded-[8px]"
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
