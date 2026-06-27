import type {
  ClusterGroup,
  ClustersResponse,
  ExamMetricsWrapper,
  QuestionDetailResponse,
  ResultsResponse,
  StatusResponse,
  SummaryResponse,
} from "@/lib/types";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string; error?: string; message?: string; code?: string };
      const message = payload.detail || payload.error || payload.message || `Request failed for ${path}`;
      throw new ApiError(message, response.status, payload.code);
    }

    const message = await response.text();
    throw new ApiError(message || `Request failed for ${path}`, response.status);
  }

  return response.json() as Promise<T>;
}

export async function uploadReferencePDF(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<{ exam_id: string; status: string }>("/api/reference/upload", {
    method: "POST",
    body: formData,
  });
}

export async function uploadStudentPDFs(examId: string, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return request<{ exam_id: string; status: string }>(`/api/exam/${examId}/students/upload`, {
    method: "POST",
    body: formData,
  });
}

export function getStatus(examId: string) {
  return request<StatusResponse>(`/api/exam/${examId}/status`);
}

export function getSummary(examId: string) {
  return request<SummaryResponse>(`/api/exam/${examId}/summary`);
}

export function getQuestionDetail(examId: string, questionId: string) {
  return request<QuestionDetailResponse>(`/api/exam/${examId}/question/${questionId}`);
}

export function getResults(examId: string) {
  return request<ResultsResponse>(`/api/exam/${examId}/results`);
}

export function getExamClusters(examId: string) {
  return request<{ exam_id: string; status?: string; clusters: Record<string, ClusterGroup[]> }>(`/api/exam/${examId}/clusters`).then(
    (payload) =>
      Object.fromEntries(
        Object.entries(payload.clusters || {}).map(([questionId, groups]) => [
          questionId,
          groups.map((group) => ({
            ...group,
            label: group.label || group.cluster_name || "Unlabeled cluster",
          })),
        ]),
      ),
  );
}

export function getExamMetrics(examId: string) {
  return request<ExamMetricsWrapper>(`/api/exam/${examId}/metrics`);
}

export function exportCsvUrl(examId: string) {
  return `/api/exam/${examId}/export`;
}

export function gradedPdfUrl(examId: string, rollNumber: string) {
  return `/api/exam/${examId}/student/${encodeURIComponent(rollNumber)}/graded-pdf`;
}

export function rawPaperUrl(examId: string, rollNumber: string) {
  return `/api/exam/${examId}/student/${encodeURIComponent(rollNumber)}/raw-paper`;
}
