"""
PDF extraction for reference answer keys and student submissions.
"""
import json

import fitz  # PyMuPDF
from dotenv import load_dotenv

from gemini_compat import (
    DEFAULT_GEMINI_MODEL,
    gemini_enabled,
    generate_content,
    make_inline_part,
    response_text,
)
from similarity_engine import merge_answer_records

load_dotenv()

GEMINI_MODEL = DEFAULT_GEMINI_MODEL

METADATA_PROMPT = """You are extracting structured data from an exam answer booklet cover page.
Extract these fields and return ONLY valid JSON (no markdown, no explanation):
{
  "student_name": "full name or null",
  "roll_number": "roll/enrollment/student ID number or null",
  "exam_code": "subject or exam code or null"
}
If a field cannot be found, use null."""

STUDENT_ANSWER_PROMPT = """You are an expert multilingual exam answer extractor.
These images are student answer-sheet pages that may contain English, Hindi, or Hinglish text.

Return ONLY valid JSON:
{
  "answers": [
    {
      "q_number": "Q1",
      "q_text": "full question text if visible, otherwise null",
      "text": "full student answer text",
      "diagram_present": false,
      "diagram_description": null,
      "attempted": true
    }
  ]
}

Rules:
- Extract one object per attempted question.
- Merge continuation text for the same question into one answer.
- Keep the question numbering accurate.
- If a diagram/sketch is present, set diagram_present=true and describe it semantically.
- Skip blank or completely unanswered questions.
- Return JSON only."""

REFERENCE_PROMPT = """You are extracting a teacher's reference answer sheet for automatic grading.
The PDF contains the correct answers for an exam.

Return ONLY valid JSON:
{
  "exam_title": "short exam title or null",
  "exam_code": "exam code or subject code or null",
  "questions": [
    {
      "q_number": "Q1",
      "q_text": "full question text",
      "max_marks": 10,
      "text": "complete reference answer text",
      "diagram_present": false,
      "diagram_description": null
    }
  ]
}

Rules:
- Extract one object per question in the answer key.
- Extract the maximum marks as a number.
- Merge continuation pages for the same question into one answer.
- Keep question numbers accurate.
- If a diagram is part of the reference answer, describe it semantically.
- Ignore non-question administrative text.
- Return JSON only."""


def _page_to_png(pdf_doc, page_num: int) -> bytes:
    page = pdf_doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    return pix.tobytes("png")


def _parse_json_response(text: str) -> dict | list:
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _build_image_contents(pdf_doc, start_page: int, prompt: str) -> list:
    content = [prompt]
    for i in range(start_page, len(pdf_doc)):
        content.append(make_inline_part(data=_page_to_png(pdf_doc, i), mime_type="image/png"))
    return content


def extract_student_metadata(pdf_doc) -> dict:
    if not gemini_enabled():
        return {"student_name": None, "roll_number": None, "exam_code": None}

    try:
        resp = generate_content(
            GEMINI_MODEL,
            [METADATA_PROMPT, make_inline_part(data=_page_to_png(pdf_doc, 0), mime_type="image/png")],
        )
        return _parse_json_response(response_text(resp))
    except Exception as exc:
        print(f"Metadata extraction failed: {exc}")
        return {"student_name": None, "roll_number": None, "exam_code": None}


def extract_student_answers(pdf_doc) -> list:
    if not gemini_enabled():
        return []

    start_page = 1 if len(pdf_doc) > 1 else 0
    try:
        resp = generate_content(GEMINI_MODEL, _build_image_contents(pdf_doc, start_page, STUDENT_ANSWER_PROMPT))
        data = _parse_json_response(response_text(resp))
        answers = data.get("answers", []) if isinstance(data, dict) else []
        return merge_answer_records(
            [answer for answer in answers if answer.get("attempted", True)],
            include_max_marks=False,
        )
    except Exception as exc:
        print(f"Student answer extraction failed: {exc}")
        return []


def extract_reference_answers(pdf_doc) -> dict:
    if not gemini_enabled():
        return {"exam_title": None, "exam_code": None, "questions": []}

    try:
        resp = generate_content(GEMINI_MODEL, _build_image_contents(pdf_doc, 0, REFERENCE_PROMPT))
        data = _parse_json_response(response_text(resp))
        if not isinstance(data, dict):
            return {"exam_title": None, "exam_code": None, "questions": []}

        questions = merge_answer_records(data.get("questions", []), include_max_marks=True)
        return {
            "exam_title": data.get("exam_title"),
            "exam_code": data.get("exam_code"),
            "questions": questions,
        }
    except Exception as exc:
        print(f"Reference answer extraction failed: {exc}")
        return {"exam_title": None, "exam_code": None, "questions": []}


def process_student_pdf(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return {"error": "Empty PDF", "student_metadata": {}, "answers": []}

    metadata = extract_student_metadata(doc)
    answers = extract_student_answers(doc)
    doc.close()
    return {"student_metadata": metadata, "answers": answers}


def process_reference_pdf(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return {"error": "Empty PDF", "exam_title": None, "exam_code": None, "questions": []}

    extracted = extract_reference_answers(doc)
    doc.close()
    return extracted
