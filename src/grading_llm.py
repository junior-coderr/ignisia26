"""
LLM-assisted rubric synthesis and grading review.

This module is optional: the deterministic scorer remains the primary grading
path, while Gemini is used to synthesize cleaner rubrics from the teacher's
reference answer and to review only low-confidence or edge-case responses.
"""
import json
import os
import re
from typing import Any

from gemini_compat import (
    DEFAULT_GEMINI_MODEL,
    gemini_enabled,
    generate_content,
    response_text,
    response_usage,
)

GRADING_MODEL = os.getenv("GRADING_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
LLM_GRADE_POLICY = os.getenv("LLM_GRADE_POLICY", "uncertain_only").strip().lower()


def _parse_json_response(text: str) -> dict | list:
    payload = (text or "").strip()
    if "```" in payload:
        parts = payload.split("```")
        payload = parts[1] if len(parts) > 1 else parts[0]
        if payload.startswith("json"):
            payload = payload[4:]
    return json.loads(payload.strip())


def _clamp(value: Any, low: float = 0.0, high: float = 1.0, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(low, min(high, numeric))


def _normalize_weights(items: list[dict]) -> list[dict]:
    cleaned = []
    total = 0.0
    for index, item in enumerate(items, start=1):
        description = str(item.get("description") or "").strip()
        if not description:
            continue
        weight = _clamp(item.get("weight"), low=0.0, high=1.0, default=0.0)
        if weight == 0.0:
            weight = 1.0
        keywords = [str(keyword).strip().lower() for keyword in item.get("keywords", []) if str(keyword).strip()]
        cleaned.append({
            "id": str(item.get("id") or f"C{index}").strip() or f"C{index}",
            "description": description,
            "weight": weight,
            "keywords": keywords[:6],
            "type": str(item.get("type") or "core").strip().lower() or "core",
        })
        total += weight

    if not cleaned:
        return []

    total = total or float(len(cleaned))
    for item in cleaned:
        item["weight"] = round(item["weight"] / total, 4)
    return cleaned


def _rubric_prompt(question: dict) -> str:
    return f"""You are building a strict teacher-facing grading rubric for ONE exam question.

Question ID: {question.get('q_number') or 'Unknown'}
Question Text: {question.get('q_text') or ''}
Maximum Marks: {question.get('max_marks') or 0}
Teacher Reference Answer:
{question.get('text') or ''}

Teacher Diagram Description:
{question.get('diagram_description') or 'None'}

Return ONLY valid JSON:
{{
  "summary": "one-sentence ideal answer summary",
  "concepts": [
    {{
      "id": "C1",
      "description": "atomic rubric point",
      "weight": 0.2,
      "keywords": ["term1", "term2"],
      "type": "core"
    }}
  ],
  "accept_alternates": ["acceptable alternate phrasing or multilingual equivalent"],
  "reject_signals": ["common wrong idea or contradiction"],
  "requires_steps": true,
  "formula_expected": "formula if relevant else null",
  "final_numeric_answer": "final result if relevant else null",
  "diagram_expected": false,
  "grading_notes": "short note for evaluator"
}}

Rules:
- Create 4 to 8 atomic rubric concepts.
- Concept weights must sum to 1.0.
- Accept equivalent English, Hindi, and Hinglish wording when the meaning matches.
- Include process steps when the teacher answer is procedural.
- Include formula/result expectations only when clearly present in the teacher answer.
- Put common misconceptions in reject_signals.
- Return JSON only."""


def build_question_rubric(question: dict) -> tuple[dict | None, dict]:
    if not gemini_enabled():
        return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    try:
        response = generate_content(GRADING_MODEL, [_rubric_prompt(question)])
        rubric = _parse_json_response(response_text(response))
        if not isinstance(rubric, dict):
            return None, response_usage(response)

        concepts = _normalize_weights(rubric.get("concepts", []))
        if not concepts:
            return None, response_usage(response)

        result = {
            "summary": str(rubric.get("summary") or "").strip(),
            "concepts": concepts,
            "accept_alternates": [str(item).strip() for item in rubric.get("accept_alternates", []) if str(item).strip()][:12],
            "reject_signals": [str(item).strip() for item in rubric.get("reject_signals", []) if str(item).strip()][:12],
            "requires_steps": bool(rubric.get("requires_steps")),
            "formula_expected": str(rubric.get("formula_expected") or "").strip() or None,
            "final_numeric_answer": str(rubric.get("final_numeric_answer") or "").strip() or None,
            "diagram_expected": bool(rubric.get("diagram_expected")),
            "grading_notes": str(rubric.get("grading_notes") or "").strip(),
        }
        return result, response_usage(response)
    except Exception as exc:
        print(f"Rubric synthesis failed for {question.get('q_number')}: {exc}")
        return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def should_run_llm_review(reference_question: dict, student_answer: dict, deterministic_grade: dict) -> bool:
    if not gemini_enabled():
        return False
    if LLM_GRADE_POLICY == "off":
        return False
    if LLM_GRADE_POLICY == "always":
        return True

    student_text = str(student_answer.get("text") or "")
    low_confidence = _clamp(deterministic_grade.get("grading_confidence"), default=0.0) < 0.74
    borderline = 0.22 <= _clamp(deterministic_grade.get("score_ratio"), default=0.0) <= 0.88
    metric_conflict = abs(
        _clamp(deterministic_grade.get("semantic_signal"), default=0.0)
        - _clamp(deterministic_grade.get("concept_coverage"), default=0.0)
    ) >= 0.22
    multilingual = bool(re.search(r"[\u0900-\u097F]", student_text))
    formula_case = bool(deterministic_grade.get("edge_case"))
    missed_many = len(deterministic_grade.get("missed_concepts", [])) >= max(2, len(reference_question.get("rubric_segments", [])) // 2)
    contradiction_count = int(deterministic_grade.get("contradiction_count") or 0)
    reject_hits = len(deterministic_grade.get("reject_hits", []))
    suspicious_semantic_gap = (
        _clamp(deterministic_grade.get("raw_similarity"), default=0.0) >= 0.72
        and _clamp(deterministic_grade.get("concept_coverage"), default=0.0) <= 0.55
    )

    return (
        formula_case
        or multilingual
        or contradiction_count > 0
        or reject_hits > 0
        or suspicious_semantic_gap
        or (borderline and low_confidence)
        or metric_conflict
        or (low_confidence and missed_many)
    )


def _review_prompt(reference_question: dict, student_answer: dict, deterministic_grade: dict) -> str:
    rubric = reference_question.get("llm_rubric") or {}
    concepts = rubric.get("concepts", [])
    serialized_concepts = json.dumps(concepts, ensure_ascii=False, indent=2)
    return f"""You are a strict, rubric-aligned exam grader for ONE answer.

Grade ONLY against the uploaded teacher reference answer and rubric.
Do not reward topical similarity if the reasoning is wrong.
Accept semantically equivalent English, Hindi, and Hinglish wording.

Question ID: {reference_question.get('q_number') or 'Unknown'}
Question Text:
{reference_question.get('q_text') or ''}

Maximum Marks: {reference_question.get('max_marks') or 0}

Teacher Reference Answer:
{reference_question.get('text') or ''}

Teacher Diagram Description:
{reference_question.get('diagram_description') or 'None'}

Structured Rubric Concepts:
{serialized_concepts}

Accept Alternates:
{json.dumps(rubric.get('accept_alternates', []), ensure_ascii=False)}

Reject Signals:
{json.dumps(rubric.get('reject_signals', []), ensure_ascii=False)}

Student Answer:
{student_answer.get('text') or ''}

Student Diagram Description:
{student_answer.get('diagram_description') or 'None'}

Deterministic Signals:
- embedding_similarity={deterministic_grade.get('similarity')}
- raw_embedding_similarity={deterministic_grade.get('raw_similarity')}
- concept_coverage={deterministic_grade.get('concept_coverage')}
- keyword_coverage={deterministic_grade.get('keyword_coverage')}
- provisional_band={deterministic_grade.get('grade_band')}
- provisional_score_ratio={deterministic_grade.get('score_ratio')}
- matched_concepts={json.dumps(deterministic_grade.get('matched_concepts', []), ensure_ascii=False)}
- missed_concepts={json.dumps(deterministic_grade.get('missed_concepts', []), ensure_ascii=False)}
- reject_hits={json.dumps(deterministic_grade.get('reject_hits', []), ensure_ascii=False)}
- contradiction_hits={json.dumps(deterministic_grade.get('contradiction_hits', []), ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "score_ratio": 0.0,
  "verdict": "correct",
  "confidence": 0.0,
  "matched_concepts": ["C1", "C2"],
  "missed_concepts": ["C3"],
  "formula_correct_calculation_wrong": false,
  "contradiction_detected": false,
  "feedback": "one short teacher-facing explanation"
}}

Rules:
- score_ratio must be between 0 and 1.
- verdict must be one of: correct, partial, incorrect, formula_half_credit.
- If the student uses the right formula/process but the arithmetic result is wrong, use formula_half_credit.
- If the answer is off-topic or contradicts the teacher answer, reduce the score strongly.
- matched_concepts and missed_concepts must use the rubric concept IDs above.
- Return JSON only."""


def review_answer_with_llm(reference_question: dict, student_answer: dict, deterministic_grade: dict) -> tuple[dict | None, dict]:
    if not gemini_enabled():
        return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    try:
        response = generate_content(GRADING_MODEL, [_review_prompt(reference_question, student_answer, deterministic_grade)])
        data = _parse_json_response(response_text(response))
        if not isinstance(data, dict):
            return None, response_usage(response)

        verdict = str(data.get("verdict") or "").strip().lower()
        if verdict not in {"correct", "partial", "incorrect", "formula_half_credit"}:
            verdict = "partial"

        result = {
            "score_ratio": _clamp(data.get("score_ratio"), default=deterministic_grade.get("score_ratio", 0.0)),
            "verdict": verdict,
            "confidence": _clamp(data.get("confidence"), default=0.5),
            "matched_concepts": [str(item).strip() for item in data.get("matched_concepts", []) if str(item).strip()],
            "missed_concepts": [str(item).strip() for item in data.get("missed_concepts", []) if str(item).strip()],
            "formula_correct_calculation_wrong": bool(data.get("formula_correct_calculation_wrong")),
            "contradiction_detected": bool(data.get("contradiction_detected")),
            "feedback": str(data.get("feedback") or "").strip(),
        }
        return result, response_usage(response)
    except Exception as exc:
        print(f"LLM grading review failed for {reference_question.get('q_number')}: {exc}")
        return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
