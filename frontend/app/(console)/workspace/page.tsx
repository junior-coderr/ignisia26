"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileText, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { UploadDropzone } from "@/components/dashboard/upload-dropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { uploadReferencePDF } from "@/lib/api";

export default function WorkspacePage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [processing, setProcessing] = useState(false);
  const [lastExamId, setLastExamId] = useState<string | null>(null);

  useEffect(() => {
    setLastExamId(window.localStorage.getItem("gradesync:lastExamId"));
  }, []);

  async function handleProcessPaper() {
    if (!files.length) {
      toast.error("Upload the teacher's reference sheet first.");
      return;
    }

    try {
      setProcessing(true);
      const response = await uploadReferencePDF(files[0]);
      window.localStorage.setItem("gradesync:lastExamId", response.exam_id);
      toast.success("Reference sheet queued for grading setup.");
      router.push(`/dashboard/${response.exam_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Reference upload failed");
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Badge variant="info">Step 1</Badge>
          <Badge variant="neutral">Upload teacher answer key</Badge>
        </div>
        <h1 className="max-w-2xl text-2xl font-semibold tracking-tight">
          Start by uploading the teacher&apos;s correct answer sheet.
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Once processed, you&apos;ll go to the dashboard to upload student PDFs and review automatic grading.
        </p>

        <div className="mt-6">
          <UploadDropzone
            title="Drop the teacher answer key here"
            subtitle="PDF or image with the correct questions and answers."
            files={files}
            onFilesChange={setFiles}
          />
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button size="lg" onClick={handleProcessPaper} disabled={processing || !files.length}>
            {processing ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Processing…
              </>
            ) : (
              <>
                <UploadCloud className="h-4 w-4" />
                Process reference sheet
              </>
            )}
          </Button>
          {lastExamId ? (
            <Button variant="secondary" size="lg" onClick={() => router.push(`/dashboard/${lastExamId}`)}>
              Resume last session
            </Button>
          ) : null}
          {processing && (
            <div className="min-w-[180px] flex-1">
              <Progress value={0} indeterminate />
            </div>
          )}
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="p-5">
          <div className="metric-label mb-3">How it works</div>
          <div className="grid gap-2">
            {[
              "Upload the teacher answer key.",
              "Wait for question extraction and embeddings.",
              "Upload student PDFs and review marks per question.",
            ].map((item, idx) => (
              <div key={item} className="flex items-start gap-3 rounded-xl border border-border/40 bg-background/50 p-3 text-sm text-muted-foreground">
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[10px] font-bold text-primary">
                  {idx + 1}
                </div>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <div className="metric-label mb-3">After upload</div>
          <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">
            <p>Upload many student PDFs in one batch.</p>
            <p>Each student answer is compared with the matching teacher answer.</p>
            <p>View grouped answer clusters and analytics.</p>
          </div>
          {lastExamId ? (
            <Button className="mt-4" variant="secondary" size="sm" onClick={() => router.push(`/dashboard/${lastExamId}`)}>
              Open last dashboard
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
