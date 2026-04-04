"""
PDF extraction for reference answer keys and student submissions.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os

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
OCR_PAGE_BATCH_SIZE = max(1, int(os.getenv("OCR_PAGE_BATCH_SIZE", "4")))
OCR_BATCH_CONCURRENCY = max(1, int(os.getenv("OCR_BATCH_CONCURRENCY", "4")))
# Render scale: 1.5 gives Gemini plenty of detail at ~44% fewer pixels than 2.0
_RENDER_SCALE = float(os.getenv("PDF_RENDER_SCALE", "1.5"))

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
      "source_pages": [2],
      "attempted": true
    }
  ]
}

Rules:
- Extract one object per attempted question.
- Merge continuation text for the same question into one answer.
- Keep the question numbering exactly as written on the sheet.
- Never invent a question number. If the number is unreadable, omit that answer instead of guessing.
- Preserve answer text faithfully; do not paraphrase into a better answer.
- Preserve important line breaks, equations, symbols, and numbered steps.
- Include source_pages showing which page numbers contributed to this answer.
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
      "diagram_description": null,
      "source_pages": [1]
    }
  ]
}

Rules:
- Extract one object per question in the answer key.
- Extract the maximum marks as a number.
- Merge continuation pages for the same question into one answer.
- Keep question numbers exactly as written.
- Never invent missing question numbers.
- Preserve the teacher's answer content faithfully; do not compress away key steps.
- Preserve important line breaks, equations, symbols, and numbered steps.
- Include source_pages showing which page numbers contributed to the extracted answer.
- If a diagram is part of the reference answer, describe it semantically.
- Ignore non-question administrative text.
- Return JSON only."""


def _page_to_jpg(pdf_doc, page_num: int, quality: int = 85) -> bytes:
    page = pdf_doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE))
    return pix.tobytes("jpeg", jpg_quality=quality)


def _page_to_png(pdf_doc, page_num: int) -> bytes:
    page = pdf_doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE))
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
        content.append(make_inline_part(data=_page_to_jpg(pdf_doc, i), mime_type="image/jpeg"))
    return content


def _build_paged_contents(pdf_doc, page_numbers: list[int], prompt: str) -> list:
    page_note = (
        f"{prompt}\n\nThe attached images correspond to original PDF pages: "
        f"{', '.join(str(page_num + 1) for page_num in page_numbers)}."
    )
    content = [page_note]
    for page_num in page_numbers:
        content.append(make_inline_part(data=_page_to_jpg(pdf_doc, page_num), mime_type="image/jpeg"))
    return content


def _build_prefetched_contents(page_numbers: list[int], prompt: str, page_images: dict[int, bytes]) -> list:
    page_note = (
        f"{prompt}\n\nThe attached images correspond to original PDF pages: "
        f"{', '.join(str(page_num + 1) for page_num in page_numbers)}."
    )
    content = [page_note]
    for page_num in page_numbers:
        content.append(make_inline_part(data=page_images[page_num], mime_type="image/jpeg"))
    return content


def _page_batches(start_page: int, total_pages: int) -> list[list[int]]:
    pages = list(range(start_page, total_pages))
    return [pages[index:index + OCR_PAGE_BATCH_SIZE] for index in range(0, len(pages), OCR_PAGE_BATCH_SIZE)]


def _extract_batch(contents: list, page_numbers: list[int]) -> tuple[list[int], dict | list]:
    response = generate_content(GEMINI_MODEL, contents)
    return page_numbers, _parse_json_response(response_text(response))


def _extract_paged_json(pdf_doc, start_page: int, prompt: str) -> list[tuple[list[int], dict | list]]:
    page_batches = _page_batches(start_page, len(pdf_doc))
    if not page_batches:
        return []

    # Pre-render all pages as JPEG in parallel using threads (pure CPU work)
    page_images: dict[int, bytes] = {}
    with ThreadPoolExecutor(max_workers=min(8, len([p for b in page_batches for p in b]))) as executor:
        futures = {
            executor.submit(_page_to_jpg, pdf_doc, page_num): page_num
            for batch in page_batches
            for page_num in batch
        }
        for future in as_completed(futures):
            page_num = futures[future]
            page_images[page_num] = future.result()
    prepared_batches = [
        (batch, _build_prefetched_contents(batch, prompt, page_images))
        for batch in page_batches
    ]

    if OCR_BATCH_CONCURRENCY <= 1 or len(prepared_batches) == 1:
        return [
            _extract_batch(contents, batch)
            for batch, contents in prepared_batches
        ]

    results: list[tuple[list[int], dict | list]] = []
    max_workers = min(OCR_BATCH_CONCURRENCY, len(prepared_batches))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_extract_batch, contents, batch): batch
            for batch, contents in prepared_batches
        }
        for future in as_completed(future_map):
            results.append(future.result())

    results.sort(key=lambda item: item[0][0] if item[0] else -1)
    return results


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
        answers = []
        for page_numbers, data in _extract_paged_json(pdf_doc, start_page, STUDENT_ANSWER_PROMPT):
            chunk_answers = data.get("answers", []) if isinstance(data, dict) else []
            for answer in chunk_answers:
                if not answer.get("source_pages"):
                    answer["source_pages"] = [page_num + 1 for page_num in page_numbers]
            answers.extend(chunk_answers)
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
        all_questions = []
        exam_title = None
        exam_code = None
        for page_numbers, data in _extract_paged_json(pdf_doc, 0, REFERENCE_PROMPT):
            if not isinstance(data, dict):
                continue
            exam_title = exam_title or data.get("exam_title")
            exam_code = exam_code or data.get("exam_code")
            chunk_questions = data.get("questions", [])
            for question in chunk_questions:
                if not question.get("source_pages"):
                    question["source_pages"] = [page_num + 1 for page_num in page_numbers]
            all_questions.extend(chunk_questions)

        questions = merge_answer_records(all_questions, include_max_marks=True)
        return {
            "exam_title": exam_title,
            "exam_code": exam_code,
            "questions": questions,
        }
    except Exception as exc:
        print(f"Reference answer extraction failed: {exc}")
        return {"exam_title": None, "exam_code": None, "questions": []}


def is_image_file(path: str) -> bool:
    return str(path).lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.heic'))

def process_student_pdf(pdf_path: str) -> dict:
    if is_image_file(pdf_path):
        with open(pdf_path, 'rb') as f:
            img_data = f.read()

        if not gemini_enabled():
            return {"student_metadata": {"student_name": None, "roll_number": None, "exam_code": None}, "answers": []}

        ext = str(pdf_path).lower()
        mime = "image/jpeg" if ext.endswith((".jpg", ".jpeg")) else "image/png"
        try:
            # Fire both Gemini calls in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                meta_future = executor.submit(
                    generate_content, GEMINI_MODEL,
                    [METADATA_PROMPT, make_inline_part(data=img_data, mime_type=mime)]
                )
                ans_future = executor.submit(
                    generate_content, GEMINI_MODEL,
                    [STUDENT_ANSWER_PROMPT, make_inline_part(data=img_data, mime_type=mime)]
                )
                meta_resp = meta_future.result()
                ans_resp = ans_future.result()

            metadata = _parse_json_response(response_text(meta_resp))
            ans_data = _parse_json_response(response_text(ans_resp))
            answers = ans_data.get("answers", []) if isinstance(ans_data, dict) else []
            merged = merge_answer_records([a for a in answers if a.get("attempted", True)], include_max_marks=False)
            return {"student_metadata": metadata, "answers": merged}
        except Exception as exc:
            print(f"Direct image processing failed: {exc}")
            return {"error": str(exc), "student_metadata": {}, "answers": []}

    # PDF path: open once, fire metadata + answer extraction in parallel
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return {"error": "Empty Document", "student_metadata": {}, "answers": []}

    try:
        if gemini_enabled():
            # Pre-render cover page only once, reuse for metadata call
            cover_jpg = _page_to_jpg(doc, 0)
            cover_part = make_inline_part(data=cover_jpg, mime_type="image/jpeg")

            with ThreadPoolExecutor(max_workers=2) as executor:
                # Metadata runs on cover page; answers run on pages 1+
                meta_future = executor.submit(
                    generate_content, GEMINI_MODEL,
                    [METADATA_PROMPT, cover_part]
                )
                ans_future = executor.submit(extract_student_answers, doc)
                metadata = _parse_json_response(response_text(meta_future.result()))
                answers = ans_future.result()
        else:
            metadata = {"student_name": None, "roll_number": None, "exam_code": None}
            answers = []
    except Exception as exc:
        print(f"Student PDF processing failed: {exc}")
        metadata = {"student_name": None, "roll_number": None, "exam_code": None}
        answers = []
    finally:
        doc.close()

    return {"student_metadata": metadata, "answers": answers}


def process_reference_pdf(pdf_path: str) -> dict:
    if is_image_file(pdf_path):
        with open(pdf_path, 'rb') as f:
            img_data = f.read()
            
        if not gemini_enabled():
            return {"exam_title": None, "exam_code": None, "questions": []}
            
        try:
            resp = generate_content(
                GEMINI_MODEL,
                [REFERENCE_PROMPT, make_inline_part(data=img_data, mime_type="image/jpeg" if str(pdf_path).lower().endswith((".jpg", ".jpeg")) else "image/png")]
            )
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
            print(f"Direct image processing failed: {exc}")
            return {"exam_title": None, "exam_code": None, "questions": []}

    # Original PyMuPDF logic for true PDFs
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return {"error": "Empty Document", "exam_title": None, "exam_code": None, "questions": []}

    extracted = extract_reference_answers(doc)
    doc.close()
    return extracted
