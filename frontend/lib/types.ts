export type ExamStatus =
  | "queued"
  | "loading"
  | "processing_reference"
  | "reference_ready"
  | "processing_students"
  | "generating_clusters"
  | "ready"
  | "error";

export interface QuestionSummary {
  q_number: string;
  q_text: string;
  max_marks: number;
  students_attempted: number;
  avg_similarity: number;
  avg_score: number;
}

export interface SummaryResponse {
  exam_id: string;
  title: string;
  exam_code: string;
  status: ExamStatus;
  reference_ready: boolean;
  total_students: number;
  question_count: number;
  max_total: number;
  class_average: number;
  questions: QuestionSummary[];
  metrics?: ExamMetricsWrapper["metrics"];
}

export interface QuestionReference {
  q_number: string;
  q_text: string;
  max_marks: number;
  text: string;
  diagram_present: boolean;
  diagram_description?: string | null;
  combined_text?: string;
  source_pages?: number[];
}

export interface RubricConcept {
  id: string;
  concept: string;
  status: "matched" | "partial" | "missed";
  match_score: number;
  coverage: number;
  weight: number;
  matched_excerpt?: string | null;
  contradiction_hits?: string[];
}

export interface StudentScore {
  attempted: boolean;
  score: number;
  score_ratio: number;
  similarity: number;
  raw_similarity?: number;
  semantic_signal: number;
  concept_coverage: number;
  keyword_coverage: number;
  structure_score: number;
  formula_score: number;
  numeric_score: number;
  strong_concept_ratio: number;
  contradiction_count?: number;
  contradiction_hits?: string[];
  grading_confidence: number;
  max_marks: number;
  student_q_text?: string | null;
  student_answer_text: string;
  student_diagram_description?: string | null;
  student_source_pages?: number[];
  reference_answer_text: string;
  reference_diagram_description?: string | null;
  reference_source_pages?: number[];
  matched_keywords: string[];
  matched_keyword_highlights: Array<{ term: string; start: number; end: number }>;
  missing_keywords: string[];
  rubric_concepts: RubricConcept[];
  matched_concepts: string[];
  matched_concept_ids?: string[];
  missed_concepts: string[];
  missed_concept_ids?: string[];
  grade_band: string;
  edge_case?: string | null;
  edge_case_confidence?: number;
  feedback_summary?: string;
  reject_hits?: string[];
  grading_method?: string;
  roll_number?: string;
  name?: string;
}

export interface QuestionDetailResponse {
  q_number: string;
  q_text: string;
  max_marks: number;
  reference_answer: QuestionReference;
  students: StudentScore[];
}

export interface StatusResponse {
  exam_id: string;
  status: ExamStatus;
  progress: number;
  error?: string | null;
  reference_ready: boolean;
  question_count?: number;
  total_students?: number;
  metrics?: ExamMetricsWrapper["metrics"];
}

export interface ResultsStudent {
  roll_number: string;
  name: string;
  exam_code: string;
  source_pdf: string;
  total: number;
  scores: Record<string, StudentScore>;
}

export interface ResultsResponse {
  exam_id: string;
  title: string;
  exam_code: string;
  status: ExamStatus;
  reference_ready?: boolean;
  questions: QuestionSummary[];
  students: ResultsStudent[];
  max_total: number;
}

export interface ClusterStudent {
  roll_number: string;
  name: string;
  answer_text: string;
  score: number;
  score_ratio: number;
  similarity: number;
  concept_coverage: number;
  keyword_coverage: number;
  structure_score: number;
  formula_score: number;
  numeric_score: number;
  grading_confidence: number;
  grade_band: string;
  edge_case?: string | null;
  matched_concepts: string[];
  missed_concepts: string[];
  matched_keywords: string[];
  matched_keyword_highlights: Array<{ term: string; start: number; end: number }>;
}

export interface ClusterStudent {
  roll_number: string;
  name: string;
  answer_text: string;
  score: number;
  score_ratio: number;
  similarity: number;
  concept_coverage: number;
  keyword_coverage: number;
  structure_score: number;
  formula_score: number;
  numeric_score: number;
  grading_confidence: number;
  grade_band: string;
  edge_case?: string | null;
  matched_concepts: string[];
  missed_concepts: string[];
  matched_keywords: string[];
  matched_keyword_highlights: Array<{ term: string; start: number; end: number }>;
}

export interface ClusterGroup {
  cluster_id: string;
  label: string;
  cluster_name?: string;
  cluster_kind?: string;
  band_kind?: string;
  band_label?: string;
  band_color?: string;
  is_outlier?: boolean;
  grade_band: string;
  grade_band_distribution?: Record<string, number>;
  dbscan_label: number;
  dbscan_eps: number;
  dbscan_min_samples: number;
  student_count: number;
  avg_score: number;
  avg_similarity: number;
  avg_confidence: number;
  avg_concept_coverage?: number;
  avg_keyword_coverage?: number;
  avg_structure_score?: number;
  score_range?: { min_ratio: number; max_ratio: number; min_score: number; max_score: number };
  common_pattern: string;
  explanation: string;
  insight: string;
  teaching_recommendation?: string;
  insights?: {
    top_missed_concepts: Array<{ concept: string; missed_count: number; missed_pct: number; matched_count: number; matched_pct: number }>;
    top_matched_concepts: Array<{ concept: string; missed_count: number; missed_pct: number; matched_count: number; matched_pct: number }>;
    misconceptions: Array<{ signal: string; count: number; percentage: number }>;
    common_matched_keywords: string[];
    grade_band_distribution: Record<string, number>;
    concept_frequency: Array<{ concept: string; matched_count: number; missed_count: number; matched_pct: number; missed_pct: number }>;
  };
  students: ClusterStudent[];
}

export type ClustersResponse = Record<string, ClusterGroup[]>;

export interface ExamMetricsWrapper {
  exam_id: string;
  status: ExamStatus;
  metrics: {
    timings: Record<string, number>;
    gemini_usage: Record<string, number>;
    llm_rubrics_built: number;
    llm_reviews_used: number;
    llm_review_candidates: number;
  };
}
