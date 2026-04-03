"""
FastAPI backend for reference-answer-based automatic grading.
"""
import asyncio
import csv
import io
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pdf_processor import process_reference_pdf, process_student_pdf
from similarity_engine import (
    cosine_similarity_score,
    encode_texts,
    make_combined_text,
    normalize_question_id,
    question_sort_key,
    similarity_to_score,
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

# In-memory exam store. A single exam is created from one teacher reference PDF.
exams: dict[str, dict] = {}


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
        "similarity": 0.0,
        "max_marks": reference_question["max_marks"],
        "student_q_text": None,
        "student_answer_text": "",
        "student_diagram_description": None,
        "reference_answer_text": reference_question["text"],
        "reference_diagram_description": reference_question.get("diagram_description"),
    }


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
    }


def _build_results_payload(exam: dict) -> dict:
    return {
        "exam_id": exam["exam_id"],
        "title": exam.get("title") or "Reference Answer Key",
        "exam_code": exam.get("exam_code", ""),
        "questions": [
            {
                "q_number": q_number,
                "q_text": exam["reference"]["questions"][q_number].get("q_text") or q_number,
                "max_marks": exam["reference"]["questions"][q_number]["max_marks"],
            }
            for q_number in exam.get("questions", [])
        ],
        "students": exam.get("students", []),
        "max_total": _max_total(exam),
    }


async def run_reference_pipeline(exam_id: str, reference_pdf_path: str):
    exam = exams[exam_id]
    exam["status"] = "processing_reference"
    exam["progress"] = 0.1

    try:
        extracted = await asyncio.to_thread(process_reference_pdf, reference_pdf_path)
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
            }
            if q_number not in order:
                order.append(q_number)

        if not normalized_questions:
            raise ValueError("No valid question IDs were extracted from the reference answer sheet")

        texts = []
        ordered_questions = sorted(order, key=question_sort_key)
        for q_number in ordered_questions:
            normalized_questions[q_number]["combined_text"] = make_combined_text(normalized_questions[q_number])
            texts.append(normalized_questions[q_number]["combined_text"])

        embeddings = await asyncio.to_thread(encode_texts, texts)
        for index, q_number in enumerate(ordered_questions):
            normalized_questions[q_number]["embedding"] = embeddings[index]

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


async def run_student_pipeline(exam_id: str, pdf_paths: list[str]):
    exam = exams[exam_id]
    if not exam.get("reference", {}).get("questions"):
        exam["status"] = "error"
        exam["error"] = "Reference answer sheet must be uploaded before student submissions"
        return

    exam["status"] = "processing_students"
    exam["progress"] = 0.05

    batch_students = []
    reference_questions = exam["reference"]["questions"]
    question_order = exam.get("questions", [])
    total = max(len(pdf_paths), 1)
    existing_count = len(exam.get("students", []))

    try:
        for idx, pdf_path in enumerate(pdf_paths):
            exam["progress"] = round(0.05 + (idx / total) * 0.55, 2)
            record = await asyncio.to_thread(process_student_pdf, pdf_path)
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
                }
            student["answers_by_question"] = answers_by_question

            for q_number in question_order:
                reference_question = reference_questions[q_number]
                if q_number not in answers_by_question:
                    student["scores"][q_number] = _missing_score_payload(reference_question)
                    continue

                answer = answers_by_question[q_number]
                if not answer.get("combined_text"):
                    student["scores"][q_number] = _missing_score_payload(reference_question)
                    continue

                embedding_jobs.append((student_index, q_number))
                texts.append(answer["combined_text"])

        if texts:
            embeddings = await asyncio.to_thread(encode_texts, texts)
            for index, (student_index, q_number) in enumerate(embedding_jobs):
                reference_question = reference_questions[q_number]
                answer = batch_students[student_index]["answers_by_question"][q_number]
                similarity = cosine_similarity_score(embeddings[index], reference_question["embedding"])
                score = similarity_to_score(similarity, reference_question["max_marks"])
                batch_students[student_index]["scores"][q_number] = {
                    "attempted": True,
                    "score": score,
                    "similarity": round(similarity, 4),
                    "max_marks": reference_question["max_marks"],
                    "student_q_text": answer.get("q_text"),
                    "student_answer_text": answer.get("text", ""),
                    "student_diagram_description": answer.get("diagram_description"),
                    "reference_answer_text": reference_question["text"],
                    "reference_diagram_description": reference_question.get("diagram_description"),
                }

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
    }


@app.get("/api/exam/{exam_id}/summary")
def get_summary(exam_id: str):
    exam = _get_exam(exam_id)
    if exam.get("status") not in {"reference_ready", "processing_students", "ready"}:
        raise HTTPException(400, f"Exam not ready for summary: {exam.get('status')}")
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
            **score,
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
    if exam.get("status") not in {"ready", "processing_students", "reference_ready"}:
        raise HTTPException(400, f"Exam results unavailable: {exam.get('status')}")
    return _build_results_payload(exam)


@app.get("/api/exam/{exam_id}/export/json")
def export_results_json(exam_id: str):
    return get_results(exam_id)


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
