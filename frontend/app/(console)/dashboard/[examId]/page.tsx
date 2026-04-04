"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Download,
  FileOutput,
  Orbit,
  RefreshCcw,
} from "lucide-react";
import { toast } from "sonner";

import { UploadDropzone } from "@/components/dashboard/upload-dropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getQuestionDetail, getStatus, getSummary, gradedPdfUrl, uploadStudentPDFs } from "@/lib/api";
import type { QuestionDetailResponse, StudentScore, SummaryResponse } from "@/lib/types";
import { formatGradeBand, highlightByTerms, initials, scoreTone } from "@/lib/utils";

function statusVariant(score?: StudentScore): "neutral" | "success" | "warning" | "danger" {
  if (!score?.attempted) return "neutral";
  if (score.grade_band === "correct") return "success";
  if (score.grade_band === "partial" || score.grade_band === "formula_half_credit") return "warning";
  return "danger";
}

export default function DashboardExamPage({ params }: { params: { examId: string } }) {
  const router = useRouter();
  const examId = params.examId;

  const [status, setStatus] = useState("loading");
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const [questionData, setQuestionData] = useState<QuestionDetailResponse | null>(null);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [studentFiles, setStudentFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let intervalId: NodeJS.Timeout;

    function handleMissingExam() {
      try {
        if (window.localStorage.getItem("gradesync:lastExamId") === examId) {
          window.localStorage.removeItem("gradesync:lastExamId");
        }
      } catch {}
      router.replace("/workspace");
    }

    async function poll() {
      try {
        const statusResponse = await getStatus(examId);
        if (cancelled) return;
        setStatus(statusResponse.status);
        setProgress(statusResponse.progress ?? 0);
        setError(statusResponse.error ?? null);

        let summaryResponse: SummaryResponse | null = null;
        try {
          summaryResponse = await getSummary(examId);
        } catch (summaryError) {
          if (summaryError instanceof ApiError && summaryError.status === 404) {
            handleMissingExam();
            return;
          }
        }

        if (cancelled) return;
        if (summaryResponse) {
          setSummary(summaryResponse);
          if (summaryResponse.questions.length) {
            const firstQuestionId = summaryResponse.questions[0].q_number;
            setQuestionId((current) => current || firstQuestionId);
          }
        }
      } catch (fetchError) {
        if (cancelled) return;
        if (fetchError instanceof ApiError && fetchError.status === 404) {
          handleMissingExam();
          return;
        }
        setStatus("error");
        setError(fetchError instanceof Error ? fetchError.message : "Failed to load session");
      }
    }

    poll();
    intervalId = setInterval(poll, 2200);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [examId, router]);

  useEffect(() => {
    if (!questionId) return;
    const currentQuestionId = questionId;
    let cancelled = false;

    async function loadQuestion() {
      try {
        const response = await getQuestionDetail(examId, currentQuestionId);
        if (cancelled) return;
        setQuestionData(response);
        setSelectedStudentId((current) => {
          if (current && response.students.some((student) => student.roll_number === current)) {
            return current;
          }
          return response.students[0]?.roll_number ?? null;
        });
      } catch (questionError) {
        if (cancelled) return;
        if (questionError instanceof ApiError && questionError.status === 404) {
          router.replace("/workspace");
          return;
        }
        setQuestionData(null);
        setError(questionError instanceof Error ? questionError.message : "Failed to load question details");
      }
    }

    loadQuestion();
    return () => {
      cancelled = true;
    };
  }, [examId, questionId, router]);

  const selectedStudent = useMemo(
    () => questionData?.students.find((student) => student.roll_number === selectedStudentId) ?? questionData?.students[0],
    [questionData, selectedStudentId],
  );

  async function handleStudentUpload() {
    if (!studentFiles.length) {
      toast.error("Upload at least one student PDF.");
      return;
    }

    try {
      setUploading(true);
      await uploadStudentPDFs(examId, studentFiles);
      toast.success("Student evaluation started.");
      setStudentFiles([]);
    } catch (uploadError) {
      toast.error(uploadError instanceof Error ? uploadError.message : "Student upload failed");
    } finally {
      setUploading(false);
    }
  }

  const questionSummary = summary?.questions.find((question) => question.q_number === questionId);
  const highlightedAnswer = selectedStudent
    ? highlightByTerms(selectedStudent.student_answer_text || "", selectedStudent.matched_keywords || [])
    : [];

  if (status === "error") {
    return (
      <Card className="mx-auto mt-20 max-w-2xl p-10 text-center">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-rose-500/10 text-rose-500">
          <AlertTriangle className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-semibold">This grading session needs attention</h1>
        <p className="mt-3 text-muted-foreground">{error || "The backend reported a session-level failure."}</p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Button variant="secondary" onClick={() => router.push("/workspace")}>
            Back to workspace
          </Button>
          <Button onClick={() => window.location.reload()}>
            <RefreshCcw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="info">{summary?.title || "Reference session"}</Badge>
              <Badge variant="neutral">{summary?.exam_code || "Exam code pending"}</Badge>
              <Badge variant={status === "ready" ? "success" : status === "processing_students" ? "warning" : "neutral"}>
                {status.replace(/_/g, " ")}
              </Badge>
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Upload student PDFs, switch questions, and review answers.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
              <span>{summary?.question_count || 0} questions</span>
              <span>{summary?.total_students || 0} students</span>
              <span>Class average {summary?.class_average || 0}/{summary?.max_total || 0}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => router.push(`/clusters/${examId}`)}>
              <Orbit className="h-4 w-4" />
              Clusters
            </Button>
            <Button variant="secondary" onClick={() => router.push(`/export/${examId}`)}>
              <FileOutput className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <CardHeader className="px-0 pt-0">
          <CardTitle>Upload student PDFs</CardTitle>
          <CardDescription>
            Upload one or more student answer sheets to start grading.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 px-0 pb-0">
          <UploadDropzone
            title="Drop student answer sheets here"
            subtitle="Page 1 is used for metadata. Remaining pages are graded question by question."
            files={studentFiles}
            onFilesChange={setStudentFiles}
            multiple
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" onClick={handleStudentUpload} disabled={uploading}>
              {uploading ? "Starting evaluation..." : "Start evaluation"}
            </Button>
            {(status === "processing_reference" || status === "processing_students") && (
              <div className="min-w-[220px] flex-1">
                <div className="mb-2 flex items-center justify-between text-sm text-muted-foreground">
                  <span>Processing</span>
                  <span>{Math.round(progress * 100)}%</span>
                </div>
                <Progress value={progress * 100} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          {summary?.questions.map((question) => (
            <Button
              key={question.q_number}
              variant={questionId === question.q_number ? "default" : "secondary"}
              size="sm"
              onClick={() => setQuestionId(question.q_number)}
            >
              {question.q_number}
            </Button>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[320px,1fr]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Students</CardTitle>
            <CardDescription>Select a student to view the answer and marks.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!questionData ? (
              Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-20 rounded-2xl" />
              ))
            ) : (
              questionData.students.map((student) => (
                <button
                  key={student.roll_number}
                  onClick={() => setSelectedStudentId(student.roll_number || null)}
                  className={`w-full rounded-3xl border p-4 text-left transition-all ${
                    selectedStudent?.roll_number === student.roll_number
                      ? "border-primary/35 bg-primary/10"
                      : "border-border/70 bg-background/70 hover:border-primary/20"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 font-semibold text-primary">
                      {initials(student.name || student.roll_number || "ST")}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <div className="truncate text-sm font-semibold">{student.name}</div>
                        <Badge variant={statusVariant(student)}>{formatGradeBand(student.grade_band)}</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">{student.roll_number}</div>
                      <div className="mt-3 flex items-center justify-between text-sm">
                        <span className={scoreTone(student.score_ratio)}>{student.score.toFixed(1)}/{student.max_marks}</span>
                        <span className="text-muted-foreground">
                          alignment {Math.round(student.similarity * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle>{questionData?.q_number || questionId || "Question"}</CardTitle>
                  <CardDescription>{questionData?.q_text || "Loading question details..."}</CardDescription>
                </div>
                <Badge variant="neutral">
                  {questionSummary?.students_attempted || 0} attempted
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-5">
              <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                <span>Average score {questionSummary?.avg_score ?? 0}/{questionSummary?.max_marks ?? questionData?.max_marks ?? 0}</span>
                <span>Average alignment {Math.round((questionSummary?.avg_similarity || 0) * 100)}%</span>
              </div>

              <div className="rounded-[28px] border border-border/70 bg-background/70 p-6">
                <div className="metric-label mb-3">Reference answer</div>
                <div className="whitespace-pre-wrap text-[15px] leading-8 text-foreground/95">
                  {questionData?.reference_answer.text || "Teacher answer is loading..."}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle>Selected student answer</CardTitle>
                  <CardDescription>
                    {selectedStudent?.name || "Select a student"} {selectedStudent?.roll_number ? `(${selectedStudent.roll_number})` : ""}
                  </CardDescription>
                </div>
                {selectedStudent ? (
                  <div className="flex items-center gap-2">
                    <Badge variant={statusVariant(selectedStudent)}>
                      {formatGradeBand(selectedStudent.grade_band)}
                    </Badge>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => window.open(gradedPdfUrl(examId, selectedStudent.roll_number || ""), "_blank")}
                    >
                      <Download className="h-4 w-4" />
                      Graded Sheet
                    </Button>
                  </div>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {!selectedStudent ? (
                <div className="space-y-3">
                  <Skeleton className="h-24 rounded-3xl" />
                  <Skeleton className="h-48 rounded-3xl" />
                </div>
              ) : (
                <>
                  <div className="rounded-[28px] border border-border/70 bg-background/70 p-5">
                    <div className="metric-label mb-2">Marks</div>
                    <div className="flex items-end justify-between gap-3">
                      <div className={`text-4xl font-semibold ${scoreTone(selectedStudent.score_ratio)}`}>
                        {selectedStudent.score.toFixed(1)}/{selectedStudent.max_marks}
                      </div>
                      <div className="text-right text-sm text-muted-foreground">
                        <div>Band: {formatGradeBand(selectedStudent.grade_band)}</div>
                        <div>Method: {selectedStudent.grading_method || "deterministic"}</div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                    <span>Alignment {Math.round(selectedStudent.similarity * 100)}%</span>
                    <span>Raw similarity {Math.round((selectedStudent.raw_similarity || 0) * 100)}%</span>
                    <span>Confidence {Math.round(selectedStudent.grading_confidence * 100)}%</span>
                  </div>

                  <div className="rounded-[28px] border border-border/70 bg-background/70 p-5">
                    <div className="mb-3 font-semibold">Student answer</div>
                    <div className="text-[15px] leading-8 text-foreground/90">
                      {highlightedAnswer.length ? (
                        highlightedAnswer.map((chunk, index) => (
                          <span
                            key={`${chunk.text}-${index}`}
                            className={
                              chunk.active
                                ? "rounded-md bg-primary/15 px-1.5 py-0.5 text-primary"
                                : ""
                            }
                          >
                            {chunk.text}
                          </span>
                        ))
                      ) : (
                        selectedStudent.student_answer_text || "No answer extracted."
                      )}
                    </div>
                  </div>

                  <div className="rounded-[28px] border border-border/70 bg-background/70 p-5">
                    <div className="mb-3 font-semibold">Rubric points</div>
                    <div className="flex flex-wrap gap-2">
                      {(selectedStudent.matched_concepts || []).map((concept) => (
                        <Badge key={concept} variant="success">
                          {concept}
                        </Badge>
                      ))}
                      {(selectedStudent.missed_concepts || []).map((concept) => (
                        <Badge key={concept} variant="warning">
                          Missing: {concept}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {(selectedStudent.reject_hits?.length || selectedStudent.contradiction_count) ? (
                    <div className="rounded-[28px] border border-rose-500/25 bg-rose-500/10 p-5">
                      <div className="mb-3 font-semibold text-rose-500">Issues found</div>
                      <div className="flex flex-wrap gap-2">
                        {selectedStudent.reject_hits?.map((hit) => (
                          <Badge key={hit} variant="danger">
                            {hit}
                          </Badge>
                        ))}
                        {selectedStudent.contradiction_hits?.map((hit) => (
                          <Badge key={hit} variant="danger">
                            {hit}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <div className="rounded-[28px] border border-border/70 bg-background/70 p-5">
                    <div className="mb-2 font-semibold">Summary</div>
                    <p className="text-sm leading-7 text-muted-foreground">
                      {selectedStudent.feedback_summary || "No explanation available yet."}
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
