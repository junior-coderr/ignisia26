"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileText, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { PipelineVisual } from "@/components/dashboard/pipeline-visual";
import { UploadDropzone } from "@/components/dashboard/upload-dropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
    <div className="space-y-6">
      <Card className="overflow-hidden p-8">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <Badge variant="info">Step 1</Badge>
          <Badge variant="neutral">Upload teacher answer key</Badge>
        </div>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight">
          Start by uploading the teacher&apos;s correct answer sheet.
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
          Once the reference sheet is processed, you&apos;ll go to the dashboard to upload student PDFs and review the
          automatic grading.
        </p>

        <div className="mt-8">
          <UploadDropzone
            title="Drop the teacher answer key here"
            subtitle="Use one PDF or image that contains the correct questions and answers."
            files={files}
            onFilesChange={setFiles}
          />
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Button size="lg" onClick={handleProcessPaper} disabled={processing || !files.length}>
            <UploadCloud className="h-4 w-4" />
            {processing ? "Processing reference..." : "Process reference sheet"}
          </Button>
          {lastExamId ? (
            <Button variant="secondary" size="lg" onClick={() => router.push(`/dashboard/${lastExamId}`)}>
              Resume last session
            </Button>
          ) : null}
        </div>
      </Card>

      <PipelineVisual activeStage={processing ? "ocr" : "embeddings"} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="metric-label mb-3">Simple flow</div>
          <div className="grid gap-3">
            {[
              "Upload the teacher answer key.",
              "Wait for question extraction and reference embeddings to finish.",
              "Upload student PDFs from the dashboard and review marks question by question.",
            ].map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-2xl border border-border/70 bg-background/70 p-4 text-sm text-muted-foreground">
                <FileText className="mt-0.5 h-4 w-4 text-primary" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="metric-label mb-3">What you can do after upload</div>
          <div className="space-y-3 text-sm leading-7 text-muted-foreground">
            <p>Upload many student PDFs in one batch.</p>
            <p>Compare each student answer only with the matching teacher answer by question ID.</p>
            <p>Open clusters later if you want grouped answer patterns, but you can use the dashboard directly.</p>
          </div>
          {lastExamId ? (
            <Button className="mt-5" variant="secondary" onClick={() => router.push(`/dashboard/${lastExamId}`)}>
              Open last dashboard
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
