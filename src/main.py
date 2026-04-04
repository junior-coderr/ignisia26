"""
FastAPI backend for reference-answer-based automatic grading.
"""
import os
# Redirect all HuggingFace / model downloads to D: drive (C: drive has no space)
os.environ.setdefault("HF_HOME", r"D:\hackathon\ignisia26\.hf_cache")
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", r"D:\hackathon\ignisia26\.hf_cache")
os.environ.setdefault("TRANSFORMERS_CACHE", r"D:\hackathon\ignisia26\.hf_cache")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", r"D:\hackathon\ignisia26\.hf_cache\hub")
import asyncio
import csv
import io
import uuid
import sys
from time import perf_counter
from pathlib import Path
from typing import Any, Callable

# Fix: Ensure the src folder is in the Python path so sibling modules are found
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pdf_processor import process_reference_pdf, process_student_pdf
from clustering_engine import run_clustering_for_question
from grading_llm import build_question_rubric, review_answer_with_llm, should_run_llm_review
from similarity_engine import (
    build_reference_profile,
    encode_texts,
    grade_answer,
    make_answer_text,
    make_combined_text,
    merge_llm_review,
    normalize_question_id,
    question_sort_key,
)

load_dotenv()

app = FastAPI(title="GradeSync AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


STUDENT_PROCESS_CONCURRENCY = _env_int("STUDENT_PROCESS_CONCURRENCY", 2)
RUBRIC_BUILD_CONCURRENCY = _env_int("RUBRIC_BUILD_CONCURRENCY", 3)
LLM_REVIEW_CONCURRENCY = _env_int("LLM_REVIEW_CONCURRENCY", 3)

# In-memory exam store. A single exam is created from one teacher reference PDF.
exams: dict[str, dict] = {}


def _timed_call(func: Callable[..., Any], *args, **kwargs) -> tuple[Any, float]:
    started_at = perf_counter()
    return func(*args, **kwargs), perf_counter() - started_at


async def _bounded_to_thread_jobs(
    jobs: list[tuple[Callable[..., Any], tuple, dict[str, Any]]],
    max_concurrency: int,
    on_complete: Callable[[int, Any], None] | None = None,
) -> list[Any]:
    if not jobs:
        return []

    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    results: list[Any] = [None] * len(jobs)

    async def _run_job(index: int, func: Callable[..., Any], args: tuple, kwargs: dict[str, Any]):
        async with semaphore:
            result = await asyncio.to_thread(func, *args, **kwargs)
        results[index] = result
        if on_complete:
            on_complete(index, result)

    await asyncio.gather(
        *(
            _run_job(index, func, args, kwargs)
            for index, (func, args, kwargs) in enumerate(jobs)
        )
    )
    return results


def _empty_metrics() -> dict:
    return {
        "timings": {
            "reference_seconds": 0.0,
            "student_seconds": 0.0,
            "clustering_seconds": 0.0,
            "ocr_seconds": 0.0,
            "embedding_seconds": 0.0,
            "rubric_seconds": 0.0,
            "llm_review_seconds": 0.0,
        },
        "gemini_usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "llm_rubrics_built": 0,
        "llm_reviews_used": 0,
        "llm_review_candidates": 0,
    }


def _add_usage(metrics: dict, usage: dict | None):
    if not usage:
        return
    bucket = metrics.setdefault("gemini_usage", {})
    bucket["prompt_tokens"] = int(bucket.get("prompt_tokens", 0) + int(usage.get("prompt_tokens", 0)))
    bucket["completion_tokens"] = int(bucket.get("completion_tokens", 0) + int(usage.get("completion_tokens", 0)))
    bucket["total_tokens"] = int(bucket.get("total_tokens", 0) + int(usage.get("total_tokens", 0)))


def _get_exam(exam_id: str) -> dict:
    exam = exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam


def _serialize_reference_question(question: dict) -> dict:
    return {
        "q_number": question["q_number"],
        "q_text": question.get("q_text") or question["q_number"],
        "max_marks": question.get("max_marks", 5.0),
        "text": question.get("text", ""),
        "diagram_present": question.get("diagram_present", False),
        "diagram_description": question.get("diagram_description"),
        "combined_text": question.get("combined_text", ""),
        "source_pages": question.get("source_pages", []),
    }


def _max_total(exam: dict) -> float:
    return round(
        sum(exam["reference"]["questions"][q]["max_marks"] for q in exam.get("questions", [])),
        1,
    )


def _missing_score_payload(reference_question: dict) -> dict:
    return {
        "attempted": False,
        "score": 0.0,
        "score_ratio": 0.0,
        "similarity": 0.0,
        "raw_similarity": 0.0,
        "semantic_signal": 0.0,
        "concept_coverage": 0.0,
        "keyword_coverage": 0.0,
        "structure_score": 0.0,
        "formula_score": 0.0,
        "numeric_score": 0.0,
        "strong_concept_ratio": 0.0,
        "contradiction_count": 0,
        "contradiction_hits": [],
        "grading_confidence": 0.0,
        "max_marks": reference_question["max_marks"],
        "student_q_text": None,
        "student_answer_text": "",
        "student_diagram_description": None,
        "student_source_pages": [],
        "reference_answer_text": reference_question["text"],
        "reference_diagram_description": reference_question.get("diagram_description"),
        "reference_source_pages": reference_question.get("source_pages", []),
        "matched_keywords": [],
        "matched_keyword_highlights": [],
        "missing_keywords": reference_question.get("rubric_keywords", []),
        "rubric_concepts": [],
        "matched_concepts": [],
        "matched_concept_ids": [],
        "missed_concepts": reference_question.get("rubric_segments", []),
        "missed_concept_ids": [],
        "grade_band": "incorrect",
        "edge_case": None,
        "edge_case_confidence": 0.0,
        "feedback_summary": "No answer extracted for this question.",
        "reject_hits": [],
        "grading_method": "missing",
    }


def _build_student_score_payload(reference_question: dict, answer: dict, grading: dict) -> dict:
    return {
        "attempted": True,
        "score": grading["score"],
        "score_ratio": grading["score_ratio"],
        "similarity": grading["similarity"],
        "raw_similarity": grading.get("raw_similarity", grading["similarity"]),
        "semantic_signal": grading["semantic_signal"],
        "concept_coverage": grading["concept_coverage"],
        "keyword_coverage": grading["keyword_coverage"],
        "structure_score": grading["structure_score"],
        "formula_score": grading["formula_score"],
        "numeric_score": grading["numeric_score"],
        "strong_concept_ratio": grading["strong_concept_ratio"],
        "contradiction_count": grading.get("contradiction_count", 0),
        "contradiction_hits": grading.get("contradiction_hits", []),
        "grading_confidence": grading["grading_confidence"],
        "max_marks": reference_question["max_marks"],
        "student_q_text": answer.get("q_text"),
        "student_answer_text": answer.get("text", ""),
        "student_diagram_description": answer.get("diagram_description"),
        "student_source_pages": answer.get("source_pages", []),
        "reference_answer_text": reference_question["text"],
        "reference_diagram_description": reference_question.get("diagram_description"),
        "reference_source_pages": reference_question.get("source_pages", []),
        "matched_keywords": grading["matched_keywords"],
        "matched_keyword_highlights": grading.get("matched_keyword_highlights", []),
        "missing_keywords": grading["missing_keywords"],
        "rubric_concepts": grading["rubric_concepts"],
        "matched_concepts": grading["matched_concepts"],
        "matched_concept_ids": grading.get("matched_concept_ids", []),
        "missed_concepts": grading["missed_concepts"],
        "missed_concept_ids": grading.get("missed_concept_ids", []),
        "grade_band": grading["grade_band"],
        "edge_case": grading["edge_case"],
        "edge_case_confidence": grading["edge_case_confidence"],
        "feedback_summary": grading.get("feedback_summary"),
        "reject_hits": grading.get("reject_hits", []),
        "grading_method": grading.get("grading_method", "deterministic"),
        "answer_embedding_vector": grading["answer_embedding_vector"],
    }


def _public_score_payload(score: dict) -> dict:
    internal_fields = {"answer_embedding_vector", "embedding_vector"}
    return {key: value for key, value in score.items() if key not in internal_fields}


def _build_summary(exam: dict) -> dict:
    questions = []
    students = exam.get("students", [])
    max_total = _max_total(exam)
    class_average = round(sum(student.get("total", 0.0) for student in students) / len(students), 1) if students else 0.0

    for q_number in exam.get("questions", []):
        reference_question = exam["reference"]["questions"][q_number]
        score_rows = [student["scores"][q_number] for student in students if q_number in student.get("scores", {})]
        attempted = [row for row in score_rows if row.get("attempted")]

        avg_similarity = round(sum(row["similarity"] for row in attempted) / len(attempted), 2) if attempted else 0.0
        avg_score = round(sum(row["score"] for row in score_rows) / len(score_rows), 1) if score_rows else 0.0

        questions.append({
            "q_number": q_number,
            "q_text": reference_question.get("q_text") or q_number,
            "max_marks": reference_question["max_marks"],
            "students_attempted": len(attempted),
            "avg_similarity": avg_similarity,
            "avg_score": avg_score,
        })

    return {
        "exam_id": exam["exam_id"],
        "title": exam.get("title") or "Reference Answer Key",
        "exam_code": exam.get("exam_code", ""),
        "status": exam.get("status"),
        "reference_ready": bool(exam.get("reference", {}).get("questions")),
        "total_students": len(students),
        "question_count": len(exam.get("questions", [])),
        "max_total": max_total,
        "class_average": class_average,
        "questions": questions,
        "metrics": exam.get("metrics", _empty_metrics()),
    }


def _build_results_payload(exam: dict) -> dict:
    return {
        "exam_id": exam["exam_id"],
        "title": exam.get("title") or "Reference Answer Key",
        "exam_code": exam.get("exam_code", ""),
        "status": exam.get("status"),
        "reference_ready": bool(exam.get("reference", {}).get("questions")),
        "questions": [
            {
                "q_number": q_number,
                "q_text": exam["reference"]["questions"][q_number].get("q_text") or q_number,
                "max_marks": exam["reference"]["questions"][q_number]["max_marks"],
            }
            for q_number in exam.get("questions", [])
        ],
        "students": [
            {
                **{key: value for key, value in student.items() if key != "scores"},
                "scores": {
                    q_number: _public_score_payload(score)
                    for q_number, score in student.get("scores", {}).items()
                },
            }
            for student in exam.get("students", [])
        ],
        "max_total": _max_total(exam),
    }


async def run_reference_pipeline(exam_id: str, reference_pdf_path: str):
    exam = exams[exam_id]
    exam["status"] = "processing_reference"
    exam["progress"] = 0.1
    exam.pop("clusters", None)
    started_at = perf_counter()

    try:
        ocr_started_at = perf_counter()
        extracted = await asyncio.to_thread(process_reference_pdf, reference_pdf_path)
        exam["metrics"]["timings"]["ocr_seconds"] = round(
            exam["metrics"]["timings"].get("ocr_seconds", 0.0) + (perf_counter() - ocr_started_at),
            3,
        )
        raw_questions = extracted.get("questions", [])
        if not raw_questions:
            raise ValueError("No questions could be extracted from the reference answer sheet")

        exam["progress"] = 0.55

        normalized_questions: dict[str, dict] = {}
        order: list[str] = []

        for question in raw_questions:
            q_number = normalize_question_id(question.get("q_number"))
            if not q_number:
                continue

            max_marks = question.get("max_marks")
            max_marks = float(max_marks) if max_marks is not None else 5.0

            normalized_questions[q_number] = {
                "q_number": q_number,
                "q_text": question.get("q_text") or q_number,
                "max_marks": max_marks,
                "text": question.get("text", ""),
                "diagram_present": question.get("diagram_present", False),
                "diagram_description": question.get("diagram_description"),
                "source_pages": question.get("source_pages", []),
            }
            if q_number not in order:
                order.append(q_number)

        if not normalized_questions:
            raise ValueError("No valid question IDs were extracted from the reference answer sheet")

        texts = []
        ordered_questions = sorted(order, key=question_sort_key)
        for q_number in ordered_questions:
            normalized_questions[q_number]["combined_text"] = make_combined_text(normalized_questions[q_number])
            normalized_questions[q_number]["answer_text"] = make_answer_text(normalized_questions[q_number])
            texts.append(normalized_questions[q_number]["answer_text"] or normalized_questions[q_number]["combined_text"])

        embedding_started_at = perf_counter()
        embeddings = await asyncio.to_thread(encode_texts, texts)
        exam["metrics"]["timings"]["embedding_seconds"] = round(
            exam["metrics"]["timings"].get("embedding_seconds", 0.0) + (perf_counter() - embedding_started_at),
            3,
        )
        for index, q_number in enumerate(ordered_questions):
            normalized_questions[q_number]["answer_embedding"] = embeddings[index]
            normalized_questions[q_number]["embedding"] = embeddings[index]

        rubric_started_at = perf_counter()
        rubric_jobs = [
            (build_question_rubric, (normalized_questions[q_number],), {})
            for q_number in ordered_questions
        ]
        rubric_results = await _bounded_to_thread_jobs(rubric_jobs, RUBRIC_BUILD_CONCURRENCY)
        for q_number, (rubric, usage) in zip(ordered_questions, rubric_results):
            _add_usage(exam["metrics"], usage)
            if rubric:
                normalized_questions[q_number]["llm_rubric"] = rubric
                exam["metrics"]["llm_rubrics_built"] += 1
            normalized_questions[q_number].update(build_reference_profile(normalized_questions[q_number]))
        exam["metrics"]["timings"]["rubric_seconds"] = round(
            exam["metrics"]["timings"].get("rubric_seconds", 0.0) + (perf_counter() - rubric_started_at),
            3,
        )

        exam["reference"] = {
            "source_pdf": reference_pdf_path,
            "questions": normalized_questions,
        }
        exam["questions"] = ordered_questions
        exam["title"] = extracted.get("exam_title") or "Reference Answer Key"
        exam["exam_code"] = extracted.get("exam_code") or ""
        exam["progress"] = 1.0
        exam["status"] = "reference_ready"
    except Exception as exc:
        exam["status"] = "error"
        exam["error"] = str(exc)
        exam["progress"] = 0.0
    finally:
        exam["metrics"]["timings"]["reference_seconds"] = round(perf_counter() - started_at, 3)


async def run_student_pipeline(exam_id: str, pdf_paths: list[str]):
    exam = exams[exam_id]
    if not exam.get("reference", {}).get("questions"):
        exam["status"] = "error"
        exam["error"] = "Reference answer sheet must be uploaded before student submissions"
        return

    exam["status"] = "processing_students"
    exam["progress"] = 0.05
    exam.pop("clusters", None)
    started_at = perf_counter()

    batch_students = []
    reference_questions = exam["reference"]["questions"]
    question_order = exam.get("questions", [])
    total = max(len(pdf_paths), 1)
    existing_count = len(exam.get("students", []))

    try:
        completed_records = 0

        def _on_student_processed(_index: int, _result: tuple[dict, float]):
            nonlocal completed_records
            completed_records += 1
            exam["progress"] = round(0.05 + (completed_records / total) * 0.55, 2)

        student_jobs = [
            (_timed_call, (process_student_pdf, pdf_path), {})
            for pdf_path in pdf_paths
        ]
        student_results = await _bounded_to_thread_jobs(
            student_jobs,
            STUDENT_PROCESS_CONCURRENCY,
            on_complete=_on_student_processed,
        )
        exam["metrics"]["timings"]["ocr_seconds"] = round(
            exam["metrics"]["timings"].get("ocr_seconds", 0.0)
            + sum(duration for _, duration in student_results),
            3,
        )

        for idx, (pdf_path, (record, _duration)) in enumerate(zip(pdf_paths, student_results)):
            metadata = record.get("student_metadata", {})

            student = {
                "roll_number": metadata.get("roll_number") or f"STU{existing_count + idx + 1:03d}",
                "name": metadata.get("student_name") or f"Student {existing_count + idx + 1}",
                "exam_code": metadata.get("exam_code") or exam.get("exam_code", ""),
                "source_pdf": Path(pdf_path).name,
                "answers": record.get("answers", []),
                "scores": {},
                "max_total": _max_total(exam),
                "total": 0.0,
            }
            batch_students.append(student)

        exam["progress"] = 0.65

        embedding_jobs = []
        texts = []
        for student_index, student in enumerate(batch_students):
            answers_by_question = {}
            for answer in student.get("answers", []):
                q_number = normalize_question_id(answer.get("q_number"))
                if not q_number:
                    continue
                answers_by_question[q_number] = {
                    **answer,
                    "q_number": q_number,
                    "combined_text": make_combined_text(answer),
                    "answer_text": make_answer_text(answer),
                    "source_pages": answer.get("source_pages", []),
                }
            student["answers_by_question"] = answers_by_question

            for q_number in question_order:
                reference_question = reference_questions[q_number]
                if q_number not in answers_by_question:
                    student["scores"][q_number] = _missing_score_payload(reference_question)
                    continue

                answer = answers_by_question[q_number]
                if not answer.get("answer_text"):
                    student["scores"][q_number] = _missing_score_payload(reference_question)
                    continue

                embedding_jobs.append((student_index, q_number))
                texts.append(answer["answer_text"])

        grading_records: list[dict[str, Any]] = []
        review_jobs: list[tuple[int, dict, dict, dict]] = []
        if texts:
            embedding_started_at = perf_counter()
            embeddings = await asyncio.to_thread(encode_texts, texts)
            exam["metrics"]["timings"]["embedding_seconds"] = round(
                exam["metrics"]["timings"].get("embedding_seconds", 0.0) + (perf_counter() - embedding_started_at),
                3,
            )
            for index, (student_index, q_number) in enumerate(embedding_jobs):
                reference_question = reference_questions[q_number]
                answer = batch_students[student_index]["answers_by_question"][q_number]
                grading = grade_answer(answer, reference_question, embeddings[index])
                if should_run_llm_review(reference_question, answer, grading):
                    exam["metrics"]["llm_review_candidates"] += 1
                    review_jobs.append((len(grading_records), reference_question, answer, grading))
                grading_records.append({
                    "student_index": student_index,
                    "q_number": q_number,
                    "answer": answer,
                    "reference_question": reference_question,
                    "grading": grading,
                })

            exam["progress"] = 0.82

            if review_jobs:
                llm_review_started_at = perf_counter()
                review_specs = [
                    (review_answer_with_llm, (reference_question, answer, grading), {})
                    for _, reference_question, answer, grading in review_jobs
                ]
                review_results = await _bounded_to_thread_jobs(review_specs, LLM_REVIEW_CONCURRENCY)
                exam["metrics"]["timings"]["llm_review_seconds"] = round(
                    exam["metrics"]["timings"].get("llm_review_seconds", 0.0) + (perf_counter() - llm_review_started_at),
                    3,
                )
                for (grading_index, _, _, _), (llm_review, usage) in zip(review_jobs, review_results):
                    _add_usage(exam["metrics"], usage)
                    if llm_review:
                        grading_record = grading_records[grading_index]
                        grading_record["grading"] = merge_llm_review(
                            grading_record["reference_question"],
                            grading_record["grading"],
                            llm_review,
                        )
                        exam["metrics"]["llm_reviews_used"] += 1

            for grading_record in grading_records:
                batch_students[grading_record["student_index"]]["scores"][grading_record["q_number"]] = _build_student_score_payload(
                    grading_record["reference_question"],
                    grading_record["answer"],
                    grading_record["grading"],
                )

        exam["progress"] = 0.96

        for student in batch_students:
            running_total = 0.0
            for q_number in question_order:
                if q_number not in student["scores"]:
                    student["scores"][q_number] = _missing_score_payload(reference_questions[q_number])
                running_total += student["scores"][q_number]["score"]
            student["total"] = round(running_total, 1)
            student.pop("answers_by_question", None)

        exam.setdefault("students", []).extend(batch_students)
        exam["progress"] = 1.0
        exam["status"] = "ready"
        exam["error"] = None
    except Exception as exc:
        exam["status"] = "error"
        exam["error"] = str(exc)
        exam["progress"] = 0.0
    finally:
        exam["metrics"]["timings"]["student_seconds"] = round(
            exam["metrics"]["timings"].get("student_seconds", 0.0) + (perf_counter() - started_at),
            3,
        )

def _run_clustering(exam: dict):
    started_at = perf_counter()
    clusters_metadata = {}
    reference_questions = exam.get("reference", {}).get("questions", {})
    students = exam.get("students", [])
    
    for q_number in exam.get("questions", []):
        ref_data = reference_questions.get(q_number)
        if not ref_data:
            continue
            
        clusters = run_clustering_for_question(q_number, ref_data, students)
        clusters_metadata[q_number] = clusters
        
    exam["clusters"] = clusters_metadata
    exam["metrics"]["timings"]["clustering_seconds"] = round(perf_counter() - started_at, 3)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/reference/upload")
async def upload_reference_answer_sheet(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(400, "Reference PDF is required")

    exam_id = f"exam_{uuid.uuid4().hex[:8]}"
    exam_dir = UPLOAD_DIR / exam_id
    exam_dir.mkdir(parents=True, exist_ok=True)
    reference_path = exam_dir / f"reference_{file.filename}"
    reference_path.write_bytes(await file.read())

    exams[exam_id] = {
        "exam_id": exam_id,
        "status": "queued",
        "progress": 0.0,
        "title": "Reference Answer Key",
        "exam_code": "",
        "reference": {},
        "questions": [],
        "students": [],
        "error": None,
        "metrics": _empty_metrics(),
    }

    background_tasks.add_task(run_reference_pipeline, exam_id, str(reference_path))
    return {"exam_id": exam_id, "status": "queued"}


@app.post("/api/exam/{exam_id}/students/upload")
async def upload_student_submissions(
    exam_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    exam = _get_exam(exam_id)
    if not exam.get("reference", {}).get("questions"):
        raise HTTPException(400, "Reference answer sheet is not ready yet")
    if not files:
        raise HTTPException(400, "At least one student PDF is required")

    exam_dir = UPLOAD_DIR / exam_id / "students"
    exam_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for file in files:
        destination = exam_dir / file.filename
        destination.write_bytes(await file.read())
        saved_paths.append(str(destination))

    background_tasks.add_task(run_student_pipeline, exam_id, saved_paths)
    return {"exam_id": exam_id, "status": "queued", "file_count": len(files)}


@app.get("/api/exam/{exam_id}/status")
def get_status(exam_id: str):
    exam = _get_exam(exam_id)
    return {
        "exam_id": exam_id,
        "status": exam.get("status"),
        "progress": exam.get("progress", 0.0),
        "reference_ready": bool(exam.get("reference", {}).get("questions")),
        "question_count": len(exam.get("questions", [])),
        "total_students": len(exam.get("students", [])),
        "error": exam.get("error"),
        "metrics": exam.get("metrics", _empty_metrics()),
    }


@app.get("/api/exam/{exam_id}/summary")
def get_summary(exam_id: str):
    exam = _get_exam(exam_id)
    return _build_summary(exam)


@app.get("/api/exam/{exam_id}/question/{q_number}")
def get_question_detail(exam_id: str, q_number: str):
    exam = _get_exam(exam_id)
    normalized_q_number = normalize_question_id(q_number)
    if not normalized_q_number:
        raise HTTPException(404, "Question not found")

    reference_question = exam.get("reference", {}).get("questions", {}).get(normalized_q_number)
    if not reference_question:
        raise HTTPException(404, f"Question {q_number} not found")

    students = []
    for student in exam.get("students", []):
        score = student.get("scores", {}).get(normalized_q_number, _missing_score_payload(reference_question))
        students.append({
            "roll_number": student["roll_number"],
            "name": student["name"],
            "exam_code": student.get("exam_code", ""),
            "source_pdf": student.get("source_pdf"),
            **_public_score_payload(score),
        })

    students.sort(key=lambda row: (-row["score"], row["roll_number"]))
    return {
        "q_number": normalized_q_number,
        "q_text": reference_question.get("q_text") or normalized_q_number,
        "max_marks": reference_question["max_marks"],
        "reference_answer": _serialize_reference_question(reference_question),
        "students": students,
    }


@app.get("/api/exam/{exam_id}/results")
def get_results(exam_id: str):
    exam = _get_exam(exam_id)
    return _build_results_payload(exam)


@app.get("/api/exam/{exam_id}/export/json")
def export_results_json(exam_id: str):
    return get_results(exam_id)


@app.get("/api/exam/{exam_id}/metrics")
def get_exam_metrics(exam_id: str):
    exam = _get_exam(exam_id)
    return {
        "exam_id": exam_id,
        "status": exam.get("status"),
        "metrics": exam.get("metrics", _empty_metrics()),
    }


@app.get("/api/exam/{exam_id}/clusters")
def get_clusters(exam_id: str):
    exam = _get_exam(exam_id)

    if exam.get("status") not in {"ready", "generating_clusters"}:
        return {
            "exam_id": exam_id,
            "status": exam.get("status"),
            "clusters": exam.get("clusters", {}),
        }

    # Lazy clustering: generate on first request only
    if "clusters" not in exam:
        try:
            _run_clustering(exam)
        except Exception as cl_err:
            print(f"Clustering error: {cl_err}")
            exam["clusters"] = {}

    return {
        "exam_id": exam_id,
        "status": exam.get("status"),
        "clusters": exam.get("clusters", {})
    }


@app.get("/api/exam/{exam_id}/export")
def export_results_csv(exam_id: str):
    exam = _get_exam(exam_id)
    question_order = exam.get("questions", [])

    output = io.StringIO()
    fieldnames = ["Roll Number", "Name", "Exam Code"]
    for q_number in question_order:
        fieldnames.append(f"{q_number} Score")
        fieldnames.append(f"{q_number} Similarity")
    fieldnames.extend(["Total", "Max Total"])

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for student in exam.get("students", []):
        row = {
            "Roll Number": student["roll_number"],
            "Name": student["name"],
            "Exam Code": student.get("exam_code", ""),
        }
        for q_number in question_order:
            score = student["scores"].get(q_number, {})
            row[f"{q_number} Score"] = score.get("score", 0.0)
            row[f"{q_number} Similarity"] = score.get("similarity", 0.0)
        row["Total"] = student.get("total", 0.0)
        row["Max Total"] = student.get("max_total", _max_total(exam))
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=grades_{exam_id}.csv"},
    )
