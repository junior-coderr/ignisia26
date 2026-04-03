"""
Phase 1: Ingestion & Smart Digitization
- Page 1 (cover) → Gemini → student metadata JSON
- Pages 2+ (answer sheets) → Gemini → per-question answer JSON
  Supports Hindi + English mixed answers
"""
import os
import json
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

GEMINI_MODEL = "gemini-2.5-flash-lite-preview-04-17"

METADATA_PROMPT = """You are extracting structured data from an exam answer booklet cover page.
Extract these fields and return ONLY valid JSON (no markdown, no explanation):
{
  "student_name": "full name or null",
  "roll_number": "roll/enrollment/student ID number or null",
  "exam_code": "subject or exam code or null"
}
If a field cannot be found, use null."""

ANSWER_PROMPT = """You are an expert multilingual exam answer extractor.
These images are answer sheet pages that may contain Hindi and/or English text.

For every question that was attempted, extract and return ONLY valid JSON (no markdown):
{
  "answers": [
    {
      "q_number": "Q1",
      "text": "full transcribed answer text. If Hindi, include Hindi text AND romanized version.",
      "diagram_present": false,
      "diagram_description": null,
      "attempted": true
    }
  ]
}

Rules:
- Skip completely blank questions entirely.
- diagram_description: if a diagram/sketch is drawn, describe it semantically (e.g. 'A right-angled triangle with sides a, b, c demonstrating Pythagoras theorem'). Otherwise null.
- Be thorough. Transcribe everything the student wrote."""


def _page_to_png(pdf_doc, page_num: int) -> bytes:
    page = pdf_doc[page_num]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")


def _parse_json_response(text: str) -> dict | list:
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def extract_metadata(pdf_doc) -> dict:
    img = _page_to_png(pdf_doc, 0)
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[METADATA_PROMPT, types.Part.from_bytes(data=img, mime_type="image/png")]
        )
        return _parse_json_response(resp.text)
    except Exception:
        return {"student_name": None, "roll_number": None, "exam_code": None}


def extract_answers(pdf_doc) -> list:
    num_pages = len(pdf_doc)
    start = 1 if num_pages > 1 else 0
    content = [ANSWER_PROMPT]
    for i in range(start, num_pages):
        content.append(types.Part.from_bytes(data=_page_to_png(pdf_doc, i), mime_type="image/png"))
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=content)
        data = _parse_json_response(resp.text)
        return data.get("answers", []) if isinstance(data, dict) else []
    except Exception:
        return []


def process_pdf(pdf_path: str) -> dict:
    """Main entry: PDF file → {student_metadata, answers}"""
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return {"error": "Empty PDF", "student_metadata": {}, "answers": []}

    metadata = extract_metadata(doc)
    answers = extract_answers(doc)
    doc.close()

    return {"student_metadata": metadata, "answers": [a for a in answers if a.get("attempted", True)]}
