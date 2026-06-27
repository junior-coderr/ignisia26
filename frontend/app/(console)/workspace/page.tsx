"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { UploadDropzone } from "@/components/dashboard/upload-dropzone";
import { Button } from "@/components/ui/button";
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
    <div className="min-h-full bg-white flex flex-col pt-16 pb-32">
      <div className="mx-auto w-full max-w-[980px] px-6 text-center">
        <h1 className="text-[40px] font-semibold tracking-[-0.01em] text-[#1d1d1f] leading-[1.1]">
          Start by uploading the teacher&apos;s answer key.
        </h1>
        <p className="mt-4 text-[24px] font-light leading-[1.5] text-[#1d1d1f]">
          Once processed, you&apos;ll upload student PDFs and review automatic grading.
        </p>

        <div className="mt-16 mx-auto max-w-[600px]">
          <UploadDropzone
            title="Drop the teacher answer key here"
            subtitle="PDF or image with the correct questions and answers."
            files={files}
            onFilesChange={setFiles}
          />
        </div>

        <div className="mt-12 flex flex-col items-center justify-center gap-6">
          <Button size="lg" onClick={handleProcessPaper} disabled={processing || !files.length}>
            {processing ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Processing…
              </>
            ) : (
              <>
                Process reference sheet
              </>
            )}
          </Button>
          
          {processing && (
            <div className="w-full max-w-[200px]">
              <Progress value={0} indeterminate />
            </div>
          )}

          {lastExamId && !processing && (
            <button 
              onClick={() => router.push(`/dashboard/${lastExamId}`)}
              className="text-[#0066cc] text-[17px] font-normal hover:underline flex items-center gap-1"
            >
              Resume last session <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
      
      <div className="mt-32 w-full bg-[#fafafc] py-24">
        <div className="mx-auto grid max-w-[980px] gap-12 px-6 lg:grid-cols-2">
          <div>
            <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7a7a7a]">
              How it works
            </div>
            <div className="space-y-6">
              {[
                "Upload the teacher answer key.",
                "Wait for question extraction and embeddings.",
                "Upload student PDFs and review marks per question.",
              ].map((item, idx) => (
                <div key={item} className="flex items-start gap-4 text-[17px] text-[#1d1d1f]">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#e0e0e0] text-[12px] font-semibold text-[#1d1d1f]">
                    {idx + 1}
                  </div>
                  <span className="leading-[1.47]">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7a7a7a]">
              After upload
            </div>
            <div className="space-y-4 text-[17px] leading-[1.47] text-[#1d1d1f]">
              <p>Upload many student PDFs in one batch.</p>
              <p>Each student answer is compared with the matching teacher answer.</p>
              <p>View grouped answer clusters and analytics.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
