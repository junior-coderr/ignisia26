"""
PDF / Image Annotation Engine for graded student answer sheets.

Produces teacher-style graded papers with:
  - Clean, minimal grading stamps on the original pages
  - Cross-document PDF links between stamps and a detailed summary
  - A professional, large-font summary section appended to the document
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


# ── Color Palette ─────────────────────────────────────────────────────────────

class C:
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

        target_w = 595
        scale = target_w / img_rect.width if img_rect.width > 0 else 1.0
        page_w = target_w
        img_h = img_rect.height * scale
        
        # Add 100px for annotation space at the top of the image
        annotation_space = 100
        page_h = img_h + annotation_space

        page = img_doc.new_page(width=page_w, height=page_h)
        page.insert_image(fitz.Rect(0, annotation_space, page_w, page_h), stream=img_bytes)
        img.close()
        return img_doc
    else:
        return fitz.open(path)


# ── Drawing primitives ────────────────────────────────────────────────────────

def _draw_tick(page: fitz.Page, cx: float, cy: float, size: float, color: tuple):
    shape = page.new_shape()
    shape.draw_line(
        fitz.Point(cx - size * 0.4, cy),
        fitz.Point(cx - size * 0.1, cy + size * 0.35),
    )
    shape.draw_line(
        fitz.Point(cx - size * 0.1, cy + size * 0.35),
        fitz.Point(cx + size * 0.45, cy - size * 0.35),
    )
    shape.finish(color=color, width=max(2.0, size * 0.14), closePath=False,
                 lineCap=1, lineJoin=1)
    shape.commit()


def _draw_cross(page: fitz.Page, cx: float, cy: float, size: float, color: tuple):
    half = size * 0.3
    shape = page.new_shape()
    shape.draw_line(fitz.Point(cx - half, cy - half), fitz.Point(cx + half, cy + half))
    shape.draw_line(fitz.Point(cx + half, cy - half), fitz.Point(cx - half, cy + half))
    shape.finish(color=color, width=max(2.0, size * 0.14), closePath=False,
                 lineCap=1, lineJoin=1)
    shape.commit()


# ── Page annotator (Stamps) ───────────────────────────────────────────────────

def _draw_stamp(page: fitz.Page, x: float, y: float, q: QuestionAnnotation) -> tuple[float, fitz.Rect]:
    """Draws a minimal grading stamp and returns (next_y, clickable_rect)."""
    color = _band_color(q.grade_band)
    bg = _band_bg(q.grade_band)
    
    w = 170
    h = 55
    
    rect = fitz.Rect(x, y, x + w, y + h)
    
    # Background
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=color, fill=bg, width=1.5)
    
    # Left bar
    shape.draw_rect(fitz.Rect(x, y, x + 8, y + h))
    shape.finish(color=color, fill=color, width=0)
    shape.commit()
    
    # Text
    writer = fitz.TextWriter(page.rect)
    writer.append(fitz.Point(x + 16, y + 20), f"{q.q_number} — {_band_label(q.grade_band)}", fontsize=12, font=fitz.Font("hebo"))
    writer.append(fitz.Point(x + 16, y + 42), f"{q.score:g} / {q.max_marks:g} Marks", fontsize=12, font=fitz.Font("helv"))
    writer.append(fitz.Point(x + w + 10, y + 34), "➔ Click for reason", fontsize=12, font=fitz.Font("helv"))
    writer.write_text(page, color=C.BLACK)
    
    # Icon
    is_correct = q.grade_band in ("correct", "excellent")
    is_partial = q.grade_band in ("partial", "formula_half_credit", "good", "average")
    cx, cy = x + w - 24, y + 27
    if is_correct:
        _draw_tick(page, cx, cy, 18, C.GREEN)
    elif is_partial:
        _draw_tick(page, cx, cy, 14, C.AMBER)
    else:
        _draw_cross(page, cx, cy, 18, C.RED)
        
    # The clickable rect will include the "Click for reason" text
    clickable_rect = fitz.Rect(x, y, x + w + 120, y + h)
    return y + h + 15, clickable_rect


def _annotate_page(page: fitz.Page, questions: list[QuestionAnnotation],
                   annotation_y_start: float | None = None) -> dict[str, tuple[int, fitz.Rect]]:
    """Returns mapping of q_number -> (page_num, stamp_rect)."""
    margin_l = 20
    y = annotation_y_start if annotation_y_start is not None else 20
    
    stamps = {}
    for q in questions:
        y, rect = _draw_stamp(page, margin_l, y, q)
        stamps[q.q_number] = (page.number, rect)
        
    return stamps


# ── Summary page ──────────────────────────────────────────────────────────────

def _wrap_text(text: str, max_width: float, fs: float) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        if fitz.get_text_length(test, fontname="helv", fontsize=fs) > max_width and current:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _build_summary_pages(doc: fitz.Document, req: StudentAnnotationRequest, stamps: dict[str, tuple[int, fitz.Rect]]):
    """Append summary pages and inject bi-directional links."""
    page = doc.new_page(width=595, height=842)
    pw, ph = page.rect.width, page.rect.height
    cx = pw / 2
    
    # ── Dark header ──
    _fill_rect(page, 0, 0, pw, 75, C.HEADER_BG)
    _text_centered(page, cx, 48, "Graded Answer Sheet — Summary", 22, C.WHITE)
    
    y = 100
    info = [
        ("Student", req.student_name),
        ("Roll No", req.roll_number),
        ("Exam", req.exam_title),
    ]
    for label, value in info:
        _text(page, 40, y, f"{label}:", 14, C.MID_GRAY)
        _text(page, 120, y, value, 16, C.BLACK)
        y += 28
        
    y += 20
    ratio = req.total_score / req.max_total if req.max_total > 0 else 0
    hero_color = C.GREEN if ratio >= 0.7 else C.AMBER if ratio >= 0.4 else C.RED
    hero_bg = _band_bg("correct" if ratio >= 0.7 else "partial" if ratio >= 0.4 else "incorrect")

    _fill_rect(page, 35, y, pw - 70, 80, hero_bg, border_color=hero_color, border_w=2.0)
    _text(page, 55, y + 45, "Total Score:", 18, C.DARK_GRAY)
    score_str = f"{req.total_score:g} / {req.max_total:g}   ({ratio * 100:.0f}%)"
    _text(page, 185, y + 48, score_str, 28, hero_color)
    
    if ratio >= 0.7:
        _draw_tick(page, pw - 80, y + 40, 40, hero_color)
    elif ratio >= 0.4:
        _draw_tick(page, pw - 80, y + 40, 32, hero_color)
    else:
        _draw_cross(page, pw - 80, y + 40, 32, hero_color)
        
    y += 120
    
    # ── Detailed Feedback Sections (paginated) ──
    sorted_qs = sorted(req.questions, key=lambda q: q.q_number)
    
    for q in sorted_qs:
        if y > ph - 250:
            page = doc.new_page(width=595, height=842)
            y = 50
            
        color = _band_color(q.grade_band)
        
        # Header Block
        _fill_rect(page, 35, y, pw - 70, 50, _band_bg(q.grade_band), border_color=color, border_w=1.5)
        _text(page, 50, y + 32, f"{q.q_number} — {_band_label(q.grade_band)}", 18, color)
        _text(page, pw - 140, y + 32, f"{q.score:g} / {q.max_marks:g}", 20, color)
        
        target_y = y  # For the inbound link
        
        # Link back to source page
        if q.q_number in stamps:
            source_page_num, stamp_rect = stamps[q.q_number]
            
            # Draw a button
            btn_rect = fitz.Rect(pw - 240, y + 10, pw - 160, y + 40)
            _fill_rect(page, btn_rect.x0, btn_rect.y0, btn_rect.width, btn_rect.height, C.WHITE, color, 1.5)
            _text(page, btn_rect.x0 + 10, btn_rect.y0 + 20, "➔ See Paper", 11, color)
            
            # Create link from summary to stamp
            page.insert_link({
                "kind": fitz.LINK_GOTO,
                "from": btn_rect,
                "page": source_page_num,
                "to": fitz.Point(stamp_rect.x0, stamp_rect.y0)
            })
            
            # Create link from stamp to summary
            source_page = doc[source_page_num]
            source_page.insert_link({
                "kind": fitz.LINK_GOTO,
                "from": stamp_rect,
                "page": page.number,
                "to": fitz.Point(35, target_y)
            })

        y += 75
        
        # Feedback text
        _text(page, 35, y, "Reason / Feedback:", 16, C.DARK_GRAY)
        y += 24
        feedback_lines = _wrap_text(q.feedback or "No feedback provided.", pw - 70, 14)
        for line in feedback_lines:
            if y > ph - 60:
                page = doc.new_page(width=595, height=842)
                y = 50
            _text(page, 35, y, line, 14, C.BLACK)
            y += 22
            
        y += 10
        
        # Concepts
        if q.matched_concepts:
            if y > ph - 60:
                page = doc.new_page(width=595, height=842)
                y = 50
            _text(page, 35, y, "✓ Matched Points:", 14, C.GREEN)
            y += 22
            for c in q.matched_concepts:
                if y > ph - 60:
                    page = doc.new_page(width=595, height=842)
                    y = 50
                _text(page, 55, y, f"• {c}", 14, C.BLACK)
                y += 20
            y += 10
            
        if q.missed_concepts:
            if y > ph - 60:
                page = doc.new_page(width=595, height=842)
                y = 50
            _text(page, 35, y, "✗ Missed Points:", 14, C.RED)
            y += 22
            for c in q.missed_concepts:
                if y > ph - 60:
                    page = doc.new_page(width=595, height=842)
                    y = 50
                _text(page, 55, y, f"• {c}", 14, C.BLACK)
                y += 20
            y += 10
            
        y += 30
        sep = page.new_shape()
        sep.draw_line(fitz.Point(35, y), fitz.Point(pw - 35, y))
        sep.finish(color=C.LIGHT_GRAY, width=1.5)
        sep.commit()
        y += 40


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
    doc = _load_document(request.source_pdf_path)
    is_img = _is_image(request.source_pdf_path)

    page_questions: dict[int, list[QuestionAnnotation]] = {}
    for q in request.questions:
        pages = q.source_pages if q.source_pages else [1]
        for page_num in pages:
            idx = page_num - 1
            if 0 <= idx < len(doc):
                page_questions.setdefault(idx, []).append(q)

    if not page_questions and len(doc) > 0:
        page_questions[0] = list(request.questions)

    all_stamps = {}
    for page_idx, questions in sorted(page_questions.items()):
        page = doc[page_idx]
        if is_img and page_idx == 0:
            annotation_start_y = 10
            stamps = _annotate_page(page, questions, annotation_y_start=annotation_start_y)
        else:
            stamps = _annotate_page(page, questions)
        all_stamps.update(stamps)

    _build_summary_pages(doc, request, all_stamps)

    buf = io.BytesIO()
    doc.save(buf, deflate=True, garbage=4)
    doc.close()
    buf.seek(0)
    return buf.read()


def annotate_student_image(request: StudentAnnotationRequest) -> bytes:
    doc = _load_document(request.source_pdf_path)

    all_stamps = {}
    if len(doc) > 0:
        page = doc[0]
        annotation_start_y = 10
        all_stamps = _annotate_page(page, request.questions, annotation_y_start=annotation_start_y)

    _build_summary_pages(doc, request, all_stamps)

    # For images, we still return the first page as PNG preview in some legacy callers,
    # but since this is now a paginated summary document, returning a PNG breaks the summary.
    # The frontend only downloads PDFs, so this PNG function might be obsolete.
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def build_annotation_request(
    exam: dict,
    student: dict,
    source_pdf_path: str,
) -> StudentAnnotationRequest:
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
