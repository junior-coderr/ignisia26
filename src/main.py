"""
FastAPI backend — GradeSync AI
Endpoints cover: upload, demo, status, clusters, grading, export
"""
import os
import asyncio
import uuid
import csv
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from pdf_processor import process_pdf
from clustering_engine import cluster_question, get_embedder
from grading_engine import grading_engine
from demo_data_generator import generate_demo_exam, RUBRIC

app = FastAPI(title="GradeSync AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store: exam_id → exam object
exams: dict = {}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────

class RubricItem(BaseModel):
    q_text: str
    max_marks: float
    keywords: list[str]

class GradeRequest(BaseModel):
    exam_id: str
    q_number: str
    cluster_id: str
    score: float
    feedback: Optional[str] = ""

class RubricSetRequest(BaseModel):
    exam_id: str
    rubric: dict[str, RubricItem]


# ─────────────────────────────────────────────────────────────
# Background processing pipeline (real PDFs)
# ─────────────────────────────────────────────────────────────

async def run_pipeline(exam_id: str, pdf_paths: list[str], rubric: dict):
    exam = exams[exam_id]
    exam["status"] = "processing"

    all_students = []
    total = len(pdf_paths)

    for idx, path in enumerate(pdf_paths):
        exam["progress"] = round(idx / total * 0.6, 2)   # 0-60% = OCR phase
        try:
            record = await asyncio.to_thread(process_pdf, path)
            meta = record.get("student_metadata", {})
            all_students.append({
                "roll_number": meta.get("roll_number") or f"STU{idx+1:03d}",
                "name": meta.get("student_name") or f"Student {idx+1}",
                "exam_code": meta.get("exam_code", ""),
                "answers": record.get("answers", []),
            })
        except Exception as e:
            print(f"Error processing {path}: {e}")

    if not all_students:
        exam["status"] = "error"
        exam["error"] = "No answers could be extracted"
        return

    exam["students"] = all_students
    exam["status"] = "clustering"
    exam["progress"] = 0.65

    # Pre-warm embedder
    await asyncio.to_thread(get_embedder)

    # Collect all question numbers across all students
    q_numbers = sorted({
        ans["q_number"]
        for stu in all_students
        for ans in stu["answers"]
    })
    exam["questions"] = q_numbers

    exam_clusters: dict = {}
    for qi, q_num in enumerate(q_numbers):
        exam["progress"] = round(0.65 + (qi / len(q_numbers)) * 0.35, 2)
        student_answers = [
            {"roll_number": stu["roll_number"], "name": stu["name"],
             "answer": ans}
            for stu in all_students
            for ans in stu["answers"]
            if ans["q_number"] == q_num
        ]
        rubric_for_q = rubric.get(q_num, {"q_text": q_num, "max_marks": 5, "keywords": []})
        result = await asyncio.to_thread(
            cluster_question, q_num, student_answers, rubric_for_q, True
        )
        exam_clusters[q_num] = result

    exam["clusters"] = exam_clusters
    exam["rubric"] = rubric
    exam["status"] = "ready"
    exam["progress"] = 1.0


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/demo")
def start_demo():
    """Instant demo — pre-clustered synthetic data, no ML needed."""
    data = generate_demo_exam()
    exam_id = data["exam_id"]
    exams[exam_id] = data
    return {"exam_id": exam_id, "status": "ready"}


@app.post("/api/upload")
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(400, "No files uploaded")

    exam_id = "exam_" + uuid.uuid4().hex[:8]
    exam_dir = UPLOAD_DIR / exam_id
    exam_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for f in files:
        dest = exam_dir / f.filename
        content = await f.read()
        dest.write_bytes(content)
        saved_paths.append(str(dest))

    exams[exam_id] = {
        "exam_id": exam_id,
        "title": "Uploaded Exam",
        "status": "queued",
        "progress": 0.0,
        "questions": [],
        "clusters": {},
        "rubric": RUBRIC,   # default rubric
        "students": [],
        "total_students": len(files),
    }

    background_tasks.add_task(run_pipeline, exam_id, saved_paths, RUBRIC)
    return {"exam_id": exam_id, "status": "queued", "file_count": len(files)}


@app.post("/api/exam/{exam_id}/rubric")
def set_rubric(exam_id: str, req: RubricSetRequest):
    if exam_id not in exams:
        raise HTTPException(404, "Exam not found")
    exams[exam_id]["rubric"] = {k: v.model_dump() for k, v in req.rubric.items()}
    return {"success": True}


@app.get("/api/exam/{exam_id}/status")
def get_status(exam_id: str):
    exam = exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    return {
        "exam_id": exam_id,
        "status": exam.get("status"),
        "progress": exam.get("progress", 0.0),
        "total_students": exam.get("total_students", 0),
        "questions": exam.get("questions", []),
    }


@app.get("/api/exam/{exam_id}/summary")
def get_summary(exam_id: str):
    exam = exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    if exam.get("status") != "ready":
        raise HTTPException(400, f"Exam not ready: {exam.get('status')}")

    clusters_by_q = exam.get("clusters", {})
    progress = grading_engine.grading_progress(exam_id, clusters_by_q)

    questions_summary = []
    for q in exam.get("questions", []):
        qdata = clusters_by_q.get(q, {})
        questions_summary.append({
            "q_number": q,
            "q_text": exam.get("rubric", {}).get(q, {}).get("q_text", q),
            "max_marks": exam.get("rubric", {}).get(q, {}).get("max_marks", 5),
            "cluster_count": len(qdata.get("clusters", [])),
            "edge_case_count": len(qdata.get("edge_cases", [])),
            "graded": progress["by_question"].get(q, {}).get("graded", 0),
            "total": progress["by_question"].get(q, {}).get("total", 0),
        })

    return {
        "exam_id": exam_id,
        "title": exam.get("title", "Exam"),
        "exam_code": exam.get("exam_code", ""),
        "total_students": exam.get("total_students", 0),
        "questions": questions_summary,
        "overall_progress": progress["overall"],
        "graded_clusters": progress["graded_clusters"],
        "total_clusters": progress["total_clusters"],
    }


@app.get("/api/exam/{exam_id}/question/{q_number}/clusters")
def get_clusters(exam_id: str, q_number: str):
    exam = exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    if exam.get("status") != "ready":
        raise HTTPException(400, "Exam not ready")

    q_data = exam.get("clusters", {}).get(q_number)
    if q_data is None:
        raise HTTPException(404, f"Question {q_number} not found")

    rubric = exam.get("rubric", {}).get(q_number, {})

    # Merge grading info
    def enrich(cluster):
        grade = grading_engine.get_cluster_grade(exam_id, cluster["cluster_id"])
        if grade:
            cluster = {**cluster, "graded": True, "score": grade["score"],
                       "feedback": grade["feedback"]}
        return cluster

    return {
        "q_number": q_number,
        "q_text": rubric.get("q_text", q_number),
        "max_marks": rubric.get("max_marks", 5),
        "rubric_keywords": rubric.get("keywords", []),
        "clusters": [enrich(c) for c in q_data.get("clusters", [])],
        "edge_cases": [enrich(c) for c in q_data.get("edge_cases", [])],
    }


@app.post("/api/grade")
def apply_grade(req: GradeRequest):
    exam = exams.get(req.exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")

    # Find cluster in exam data
    q_data = exam.get("clusters", {}).get(req.q_number)
    if not q_data:
        raise HTTPException(404, "Question not found")

    all_clusters = q_data.get("clusters", []) + q_data.get("edge_cases", [])
    target = next((c for c in all_clusters if c["cluster_id"] == req.cluster_id), None)
    if not target:
        raise HTTPException(404, "Cluster not found")

    count = grading_engine.apply_grade(
        exam_id=req.exam_id,
        q_number=req.q_number,
        cluster_id=req.cluster_id,
        students=target["students"],
        score=req.score,
        feedback=req.feedback or "",
    )

    # Update in-memory cluster graded flag
    target["graded"] = True
    target["score"] = req.score
    target["feedback"] = req.feedback or ""

    progress = grading_engine.grading_progress(req.exam_id, exam.get("clusters", {}))
    return {
        "success": True,
        "students_graded": count,
        "overall_progress": progress["overall"],
        "graded_clusters": progress["graded_clusters"],
        "total_clusters": progress["total_clusters"],
    }


@app.get("/api/exam/{exam_id}/export")
def export_grades(exam_id: str):
    exam = exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")

    questions = exam.get("questions", [])
    all_students = exam.get("students", [])
    student_grades = grading_engine.get_student_grades(exam_id)
    grades_by_roll = {g["roll_number"]: g for g in student_grades}

    # Build rows
    rows = []
    for stu in all_students:
        roll = stu["roll_number"]
        g = grades_by_roll.get(roll, {})
        scores = g.get("scores", {})
        row = {
            "Roll Number": roll,
            "Name": stu.get("name", ""),
        }
        total = 0.0
        max_total = 0.0
        for q in questions:
            rubric = exam.get("rubric", {}).get(q, {})
            max_m = rubric.get("max_marks", 5)
            max_total += max_m
            sc = scores.get(q, {}).get("score")
            row[f"{q} Score"] = sc if sc is not None else "Not graded"
            row[f"{q} Feedback"] = scores.get(q, {}).get("feedback", "")
            if sc is not None:
                total += sc
        row["Total"] = round(total, 1)
        row["Max Total"] = max_total
        rows.append(row)

    # Stream as CSV
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=grades_{exam_id}.csv"}
    )


@app.get("/api/exam/{exam_id}/export/json")
def export_grades_json(exam_id: str):
    exam = exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")

    questions = exam.get("questions", [])
    all_students = exam.get("students", [])
    student_grades = grading_engine.get_student_grades(exam_id)
    grades_by_roll = {g["roll_number"]: g for g in student_grades}

    results = []
    for stu in all_students:
        roll = stu["roll_number"]
        g = grades_by_roll.get(roll, {})
        scores = g.get("scores", {})
        per_q = {}
        total = 0.0
        for q in questions:
            sc = scores.get(q, {}).get("score")
            per_q[q] = {"score": sc, "feedback": scores.get(q, {}).get("feedback", "")}
            if sc is not None:
                total += sc
        results.append({
            "roll_number": roll,
            "name": stu.get("name", ""),
            "scores": per_q,
            "total": round(total, 1),
        })

    return {"exam_id": exam_id, "students": results}
