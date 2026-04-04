"""
PDF / Image Annotation Engine for graded student answer sheets.

Produces teacher-style graded papers with:
  - Large ✓ / ✗ marks drawn on the page
  - Circled scores beside each answer region
  - Color-coded highlight strips with feedback
  - Concept match/miss pills
  - A professional summary page
  - Support for both PDF and image (JPG/PNG) inputs
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF


# ── Color Palette ─────────────────────────────────────────────────────────────

class C:
    """Grading color constants (RGB 0-1)."""
    GREEN       = (0.133, 0.773, 0.369)
    GREEN_LIGHT = (0.85, 0.96, 0.88)
    AMBER       = (0.961, 0.620, 0.043)
    AMBER_LIGHT = (0.99, 0.95, 0.85)
    RED         = (0.937, 0.267, 0.267)
    RED_LIGHT   = (0.98, 0.88, 0.88)
    WHITE       = (1.0, 1.0, 1.0)
    BLACK       = (0.10, 0.10, 0.12)
    DARK_GRAY   = (0.30, 0.30, 0.32)
    MID_GRAY    = (0.55, 0.55, 0.58)
    LIGHT_GRAY  = (0.93, 0.93, 0.95)
    HEADER_BG   = (0.14, 0.14, 0.20)


def _band_color(band: str) -> tuple:
    if band in ("correct", "excellent"):
        return C.GREEN
    if band in ("partial", "formula_half_credit", "good"):
        return C.AMBER
    if band in ("average",):
        return C.AMBER
    return C.RED


def _band_bg(band: str) -> tuple:
    if band in ("correct", "excellent"):
        return C.GREEN_LIGHT
    if band in ("partial", "formula_half_credit", "good", "average"):
        return C.AMBER_LIGHT
    return C.RED_LIGHT


def _band_label(band: str) -> str:
    labels = {
        "correct": "Correct", "excellent": "Excellent", "good": "Good",
        "partial": "Partial", "average": "Average",
        "formula_half_credit": "Formula ✓ Calc ✗",
        "incorrect": "Incorrect", "poor": "Needs Improvement",
    }
    return labels.get(band, "Review")


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class QuestionAnnotation:
    q_number: str
    score: float
    max_marks: float
    grade_band: str
    matched_concepts: list[str] = field(default_factory=list)
    missed_concepts: list[str] = field(default_factory=list)
    feedback: str = ""
    source_pages: list[int] = field(default_factory=list)  # 1-indexed


@dataclass
class StudentAnnotationRequest:
    student_name: str
    roll_number: str
    exam_title: str
    total_score: float
    max_total: float
    source_pdf_path: str
    questions: list[QuestionAnnotation] = field(default_factory=list)


# ── Helper: image file detection ──────────────────────────────────────────────

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".heic"}


def _is_image(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTS


# ── Loader: open PDF or image as fitz.Document ────────────────────────────────

def _load_document(path: str) -> fitz.Document:
    """
    Open a PDF or image file as a fitz.Document.
    Images are embedded as full-page PDF content at a readable size.
    """
    p = Path(path)
    if not p.exists():
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        return doc

    if _is_image(path):
        img_doc = fitz.open()
        img_bytes = p.read_bytes()
        img = fitz.open(stream=img_bytes, filetype=p.suffix.lstrip("."))

        page0 = img[0]
        img_rect = page0.rect

        # Scale image to fill an A4-width page (595pt) while keeping aspect ratio
        # Add extra vertical space below the image for annotations
        target_w = 595
        scale = target_w / img_rect.width if img_rect.width > 0 else 1.0
        page_w = target_w
        img_h = img_rect.height * scale
        # Add 40% extra height below image for annotation overlays
        annotation_space = max(300, img_h * 0.4)
        page_h = img_h + annotation_space

        page = img_doc.new_page(width=page_w, height=page_h)
        page.insert_image(fitz.Rect(0, 0, page_w, img_h), stream=img_bytes)
        img.close()
        return img_doc
    else:
        return fitz.open(path)


# ── Drawing primitives ────────────────────────────────────────────────────────

def _draw_tick(page: fitz.Page, cx: float, cy: float, size: float, color: tuple):
    """Draw a large ✓ checkmark."""
    shape = page.new_shape()
    shape.draw_line(
        fitz.Point(cx - size * 0.4, cy),
        fitz.Point(cx - size * 0.1, cy + size * 0.35),
    )
    shape.draw_line(
        fitz.Point(cx - size * 0.1, cy + size * 0.35),
        fitz.Point(cx + size * 0.45, cy - size * 0.35),
    )
    shape.finish(color=color, width=max(3.0, size * 0.14), closePath=False,
                 lineCap=1, lineJoin=1)
    shape.commit()


def _draw_cross(page: fitz.Page, cx: float, cy: float, size: float, color: tuple):
    """Draw a large ✗ cross mark."""
    half = size * 0.3
    shape = page.new_shape()
    shape.draw_line(fitz.Point(cx - half, cy - half), fitz.Point(cx + half, cy + half))
    shape.draw_line(fitz.Point(cx + half, cy - half), fitz.Point(cx - half, cy + half))
    shape.finish(color=color, width=max(3.0, size * 0.14), closePath=False,
                 lineCap=1, lineJoin=1)
    shape.commit()


def _draw_circled_score(page: fitz.Page, cx: float, cy: float, radius: float,
                        score: float, max_marks: float, color: tuple):
    """Draw a score inside a stroked circle (teacher-style)."""
    shape = page.new_shape()
    shape.draw_circle(fitz.Point(cx, cy), radius)
    shape.finish(color=color, fill=C.WHITE, width=2.5)
    shape.commit()

    score_text = f"{score:g}/{max_marks:g}"
    fs = min(18, radius * 0.75)
    tw = fitz.get_text_length(score_text, fontname="helv", fontsize=fs)
    writer = fitz.TextWriter(page.rect)
    writer.append(fitz.Point(cx - tw / 2, cy + fs * 0.35), score_text,
                  fontsize=fs, font=fitz.Font("helv"))
    writer.write_text(page, color=color)


def _draw_feedback_strip(page: fitz.Page, x: float, y: float, width: float,
                         text: str, color: tuple, bg: tuple) -> float:
    """Draw a colored feedback strip with wrapped text. Returns Y after strip."""
    if not text:
        return y

    fs = 12
    padding = 10
    line_h = fs + 5

    # Word-wrap
    words = text.split()
    lines: list[str] = []
    current = ""
    inner_w = width - padding * 2 - 8
    for word in words:
        test = f"{current} {word}".strip()
        if fitz.get_text_length(test, fontname="helv", fontsize=fs) > inner_w and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    strip_h = padding * 2 + len(lines) * line_h + 2

    # Background
    shape = page.new_shape()
    rect = fitz.Rect(x, y, x + width, y + strip_h)
    shape.draw_rect(rect)
    shape.finish(color=color, fill=bg, width=1.0)
    shape.commit()

    # Left accent bar
    accent = page.new_shape()
    accent.draw_rect(fitz.Rect(x, y, x + 4, y + strip_h))
    accent.finish(color=color, fill=color, width=0)
    accent.commit()

    # Text
    writer = fitz.TextWriter(page.rect)
    text_y = y + padding + fs
    for line in lines:
        writer.append(fitz.Point(x + padding + 6, text_y), line,
                      fontsize=fs, font=fitz.Font("helv"))
        text_y += line_h
    writer.write_text(page, color=C.DARK_GRAY)

    return y + strip_h + 6


def _draw_concept_row(page: fitz.Page, x: float, y: float, max_width: float,
                      concepts: list[str], color: tuple, symbol: str) -> float:
    """Draw a row of concept pills. Returns Y after the row."""
    if not concepts:
        return y

    fs = 10
    pill_h = 20
    gap = 6
    cx = x
    row_y = y

    for concept in concepts[:6]:
        label = f" {symbol} {concept} "
        tw = fitz.get_text_length(label, fontname="helv", fontsize=fs)
        pill_w = tw + 12

        if cx + pill_w > x + max_width and cx > x:
            cx = x
            row_y += pill_h + 4

        # Pill background
        pr = fitz.Rect(cx, row_y, cx + pill_w, row_y + pill_h)
        shape = page.new_shape()
        shape.draw_rect(pr)
        shape.finish(color=color, fill=(*color[:3], 0.12) if len(color) == 3 else color,
                     width=0.8)
        shape.commit()

        # Pill text
        writer = fitz.TextWriter(page.rect)
        writer.append(fitz.Point(cx + 6, row_y + pill_h - 5), label,
                      fontsize=fs, font=fitz.Font("helv"))
        writer.write_text(page, color=color)

        cx += pill_w + gap

    return row_y + pill_h + 6


def _draw_question_label(page: fitz.Page, x: float, y: float,
                         q_number: str, band: str, color: tuple) -> float:
    """Draw a bold question header label like 'Q1 — Correct'. Returns Y after."""
    label = f"{q_number}  —  {_band_label(band)}"
    fs = 14
    writer = fitz.TextWriter(page.rect)
    writer.append(fitz.Point(x, y + fs), label, fontsize=fs, font=fitz.Font("helv"))
    writer.write_text(page, color=color)
    return y + fs + 8


# ── Page annotator ────────────────────────────────────────────────────────────

def _annotate_page(page: fitz.Page, questions: list[QuestionAnnotation],
                   annotation_y_start: float | None = None):
    """
    Draw teacher-style annotations on a single page.
    If annotation_y_start is given, annotations begin at that Y position
    (used for images where we want to annotate below the image).
    """
    pw = page.rect.width
    ph = page.rect.height

    margin_l = 20
    margin_r = 20
    content_w = pw - margin_l - margin_r
    score_radius = 28
    mark_size = 34

    # Start annotations either below image or at top of page
    y = annotation_y_start if annotation_y_start is not None else 14

    for q in questions:
        color = _band_color(q.grade_band)
        bg = _band_bg(q.grade_band)
        is_correct = q.grade_band in ("correct", "excellent")
        is_partial = q.grade_band in ("partial", "formula_half_credit", "good", "average")

        block_top = y

        # ── Large ✓ or ✗ mark ──
        mark_x = margin_l + mark_size * 0.5
        mark_y = y + mark_size * 0.5
        if is_correct:
            _draw_tick(page, mark_x, mark_y, mark_size, C.GREEN)
        elif is_partial:
            _draw_tick(page, mark_x, mark_y, mark_size * 0.85, C.AMBER)
            wave_shape = page.new_shape()
            wave_shape.draw_line(
                fitz.Point(mark_x + mark_size * 0.3, mark_y + mark_size * 0.1),
                fitz.Point(mark_x + mark_size * 0.55, mark_y - mark_size * 0.1),
            )
            wave_shape.finish(color=C.AMBER, width=2.0, closePath=False)
            wave_shape.commit()
        else:
            _draw_cross(page, mark_x, mark_y, mark_size, C.RED)

        # ── Circled score (top-right) ──
        score_cx = pw - margin_r - score_radius - 6
        score_cy = y + score_radius + 4
        _draw_circled_score(page, score_cx, score_cy, score_radius,
                            q.score, q.max_marks, color)

        # ── Question label ──
        label_x = margin_l + mark_size + 12
        y = _draw_question_label(page, label_x, y, q.q_number, q.grade_band, color)

        # ── Feedback strip ──
        strip_x = margin_l + 6
        strip_w = content_w - score_radius * 2 - 24
        if q.feedback:
            y = _draw_feedback_strip(page, strip_x, y, strip_w,
                                     q.feedback, color, bg)

        # ── Concept pills ──
        pill_x = margin_l + 6
        pill_w = content_w - 12
        if q.matched_concepts:
            y = _draw_concept_row(page, pill_x, y, pill_w,
                                  q.matched_concepts, C.GREEN, "✓")
        if q.missed_concepts:
            y = _draw_concept_row(page, pill_x, y, pill_w,
                                  q.missed_concepts, C.RED, "✗")

        # ── Left color bar spanning the entire block ──
        bar_h = max(y - block_top, mark_size + 10)
        bar_shape = page.new_shape()
        bar_shape.draw_rect(fitz.Rect(margin_l - 8, block_top, margin_l - 3, block_top + bar_h))
        bar_shape.finish(color=color, fill=color, width=0)
        bar_shape.commit()

        # ── Separator line ──
        y += 6
        sep = page.new_shape()
        sep.draw_line(fitz.Point(margin_l, y), fitz.Point(pw - margin_r, y))
        sep.finish(color=C.LIGHT_GRAY, width=0.6)
        sep.commit()
        y += 10


# ── Summary page ──────────────────────────────────────────────────────────────

def _build_summary_page(doc: fitz.Document, req: StudentAnnotationRequest):
    """Append a professional grading summary page."""
    page = doc.new_page(width=595, height=842)
    pw, ph = page.rect.width, page.rect.height
    cx = pw / 2

    # ── Dark header ──
    _fill_rect(page, 0, 0, pw, 65, C.HEADER_BG)
    _text_centered(page, cx, 42, "Graded Answer Sheet — Summary", 18, C.WHITE)

    # ── Student info block ──
    y = 85
    info = [
        ("Student", req.student_name),
        ("Roll No", req.roll_number),
        ("Exam", req.exam_title),
    ]
    for label, value in info:
        _text(page, 40, y, f"{label}:", 11, C.MID_GRAY)
        _text(page, 110, y, value, 12, C.BLACK)
        y += 22

    # ── Score hero ──
    y += 10
    ratio = req.total_score / req.max_total if req.max_total > 0 else 0
    hero_color = C.GREEN if ratio >= 0.7 else C.AMBER if ratio >= 0.4 else C.RED
    hero_bg = _band_bg("correct" if ratio >= 0.7 else "partial" if ratio >= 0.4 else "incorrect")

    _fill_rect(page, 35, y, pw - 70, 56, hero_bg, border_color=hero_color, border_w=1.5)
    _text(page, 52, y + 26, "Total Score:", 13, C.DARK_GRAY)
    score_str = f"{req.total_score:g} / {req.max_total:g}   ({ratio * 100:.0f}%)"
    _text(page, 155, y + 26, score_str, 16, hero_color)

    if ratio >= 0.7:
        _draw_tick(page, pw - 75, y + 28, 28, hero_color)
    elif ratio >= 0.4:
        _draw_tick(page, pw - 75, y + 28, 24, hero_color)
    else:
        _draw_cross(page, pw - 75, y + 28, 24, hero_color)

    y += 72

    # ── Table ──
    col_x = [40, 95, 155, 215, 300, 400]
    headers = ["Q.No", "Score", "Max", "Band", "Feedback", "Concepts"]

    _fill_rect(page, 35, y - 2, pw - 70, 24, C.LIGHT_GRAY, border_color=C.MID_GRAY, border_w=0.5)
    for i, h in enumerate(headers):
        _text(page, col_x[i], y + 14, h, 10, C.DARK_GRAY)
    y += 28

    sorted_qs = sorted(req.questions, key=lambda q: q.q_number)
    for idx, q in enumerate(sorted_qs):
        color = _band_color(q.grade_band)

        if idx % 2 == 0:
            _fill_rect(page, 35, y - 2, pw - 70, 24, (0.98, 0.98, 0.99))

        dot_shape = page.new_shape()
        dot_shape.draw_circle(fitz.Point(col_x[0] - 7, y + 9), 4)
        dot_shape.finish(color=color, fill=color, width=0)
        dot_shape.commit()

        _text(page, col_x[0], y + 14, q.q_number, 11, C.BLACK)
        _text(page, col_x[1], y + 14, f"{q.score:g}", 11, color)
        _text(page, col_x[2], y + 14, f"{q.max_marks:g}", 11, C.DARK_GRAY)
        _text(page, col_x[3], y + 14, _band_label(q.grade_band), 10, color)

        fb_short = (q.feedback[:35] + "…") if len(q.feedback) > 38 else q.feedback
        _text(page, col_x[4], y + 14, fb_short, 9, C.MID_GRAY)

        matched = len(q.matched_concepts)
        missed = len(q.missed_concepts)
        if matched or missed:
            concept_info = f"✓{matched}  ✗{missed}"
            _text(page, col_x[5], y + 14, concept_info, 10,
                  C.GREEN if missed == 0 else C.RED if matched == 0 else C.AMBER)

        y += 24

        if y > ph - 60:
            break

    # ── Footer ──
    footer = "Generated by GradeSync AI — Automated Grading System"
    _text_centered(page, cx, ph - 20, footer, 8, C.MID_GRAY)


# ── Text/rect helpers ─────────────────────────────────────────────────────────

def _text(page: fitz.Page, x: float, y: float, text: str, fs: float, color: tuple):
    writer = fitz.TextWriter(page.rect)
    writer.append(fitz.Point(x, y), text, fontsize=fs, font=fitz.Font("helv"))
    writer.write_text(page, color=color)


def _text_centered(page: fitz.Page, cx: float, y: float, text: str, fs: float, color: tuple):
    tw = fitz.get_text_length(text, fontname="helv", fontsize=fs)
    _text(page, cx - tw / 2, y, text, fs, color)


def _fill_rect(page: fitz.Page, x: float, y: float, w: float, h: float,
               fill: tuple, border_color: tuple | None = None, border_w: float = 0):
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(x, y, x + w, y + h))
    shape.finish(color=border_color or fill, fill=fill, width=border_w)
    shape.commit()


# ── Public API ────────────────────────────────────────────────────────────────

def annotate_student_pdf(request: StudentAnnotationRequest) -> bytes:
    """
    Open the student's original PDF or image, overlay grading annotations,
    append a summary page, and return the result as PDF bytes.
    """
    doc = _load_document(request.source_pdf_path)
    is_img = _is_image(request.source_pdf_path)

    # Map pages → questions (source_pages are 1-indexed)
    page_questions: dict[int, list[QuestionAnnotation]] = {}
    for q in request.questions:
        pages = q.source_pages if q.source_pages else [1]
        for page_num in pages:
            idx = page_num - 1
            if 0 <= idx < len(doc):
                page_questions.setdefault(idx, []).append(q)

    # Fallback: all questions on page 0
    if not page_questions and len(doc) > 0:
        page_questions[0] = list(request.questions)

    # Annotate each page
    for page_idx, questions in sorted(page_questions.items()):
        page = doc[page_idx]
        if is_img and page_idx == 0:
            # For images: figure out where the image ends so
            # annotations go below the image, not on top of it
            img_list = page.get_images(full=True)
            if img_list:
                # Image fills from y=0 to roughly 60% of page height
                # (we added 40% annotation space in _load_document)
                annotation_start_y = page.rect.height * 0.60 + 10
            else:
                annotation_start_y = page.rect.height * 0.55
            _annotate_page(page, questions, annotation_y_start=annotation_start_y)
        else:
            _annotate_page(page, questions)

    # Summary page
    _build_summary_page(doc, request)

    # Output
    buf = io.BytesIO()
    doc.save(buf, deflate=True, garbage=4)
    doc.close()
    buf.seek(0)
    return buf.read()


def annotate_student_image(request: StudentAnnotationRequest) -> bytes:
    """
    Same as annotate_student_pdf but returns the first annotated page
    as a PNG image (for single-image inputs).
    """
    doc = _load_document(request.source_pdf_path)

    if len(doc) > 0:
        page = doc[0]
        img_list = page.get_images(full=True)
        if img_list:
            annotation_start_y = page.rect.height * 0.60 + 10
        else:
            annotation_start_y = page.rect.height * 0.55
        _annotate_page(doc[0], request.questions, annotation_y_start=annotation_start_y)

    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def build_annotation_request(
    exam: dict,
    student: dict,
    source_pdf_path: str,
) -> StudentAnnotationRequest:
    """Bridge the main.py data model to the annotator data model."""
    questions = []
    for q_number in exam.get("questions", []):
        score_data = student.get("scores", {}).get(q_number)
        if not score_data:
            continue

        questions.append(QuestionAnnotation(
            q_number=q_number,
            score=float(score_data.get("score", 0)),
            max_marks=float(score_data.get("max_marks", 5)),
            grade_band=score_data.get("grade_band", "incorrect"),
            matched_concepts=list(score_data.get("matched_concepts", [])),
            missed_concepts=list(score_data.get("missed_concepts", [])),
            feedback=str(score_data.get("feedback_summary", "") or ""),
            source_pages=list(score_data.get("student_source_pages", [])),
        ))

    ref_questions = exam.get("reference", {}).get("questions", {})
    max_total = sum(
        ref_questions[q]["max_marks"]
        for q in exam.get("questions", [])
        if q in ref_questions
    )

    return StudentAnnotationRequest(
        student_name=student.get("name", "Unknown"),
        roll_number=student.get("roll_number", "Unknown"),
        exam_title=exam.get("title", "Exam"),
        total_score=float(student.get("total", 0)),
        max_total=round(max_total, 1),
        source_pdf_path=source_pdf_path,
        questions=questions,
    )
