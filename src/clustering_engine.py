"""
Score-band clustering for graded student answers.

Students are grouped into performance tiers based on their score relative to
max marks for each question. Within each tier, rich insights are extracted:
common missed/matched concepts, misconceptions, patterns, etc.
"""
from collections import Counter, defaultdict

import numpy as np


# ── Score Bands ──────────────────────────────────────────────────────────────
# Each band is defined as (lower_ratio, upper_ratio, label, kind, color_hint)

SCORE_BANDS = [
    (0.0,  0.40, "Needs Improvement",    "poor",      "#ef4444"),
    (0.40, 0.70, "Average Understanding", "average",   "#f59e0b"),
    (0.70, 0.90, "Good Understanding",    "good",      "#3b82f6"),
    (0.90, 1.01, "Excellent",             "excellent", "#22c55e"),
]


def _get_band(score_ratio: float) -> tuple[str, str, str]:
    """Return (band_label, band_kind, color_hint) for a given score ratio."""
    for low, high, label, kind, color in SCORE_BANDS:
        if low <= score_ratio < high:
            return label, kind, color
    return SCORE_BANDS[-1][2], SCORE_BANDS[-1][3], SCORE_BANDS[-1][4]


def _mean(items: list[dict], key: str) -> float:
    if not items:
        return 0.0
    return round(sum(float(item.get(key, 0.0)) for item in items) / len(items), 3)


def _join_top(values: list[str], empty_text: str, limit: int = 3) -> str:
    counts = Counter(value for value in values if value)
    if not counts:
        return empty_text
    return ", ".join(value for value, _ in counts.most_common(limit))


def _percentage(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((count / total) * 100, 1)


# ── Insight Extraction ───────────────────────────────────────────────────────

def _extract_insights(items: list[dict], band_label: str, band_kind: str) -> dict:
    """Extract rich insights from a group of students in the same score band."""

    # Concept analysis
    all_matched = [c for item in items for c in item.get("matched_concepts", [])]
    all_missed = [c for item in items for c in item.get("missed_concepts", [])]
    all_reject_hits = [r for item in items for r in item.get("reject_hits", [])]
    all_keywords = [k for item in items for k in item.get("matched_keywords", [])]

    matched_counts = Counter(all_matched)
    missed_counts = Counter(all_missed)
    reject_counts = Counter(all_reject_hits)
    keyword_counts = Counter(all_keywords)

    # Concept frequency analysis (what % of students in this band matched/missed each concept)
    concept_frequency = {}
    all_concepts = set(all_matched + all_missed)
    for concept in all_concepts:
        matched_n = sum(1 for item in items if concept in item.get("matched_concepts", []))
        missed_n = sum(1 for item in items if concept in item.get("missed_concepts", []))
        concept_frequency[concept] = {
            "concept": concept,
            "matched_count": matched_n,
            "missed_count": missed_n,
            "matched_pct": _percentage(matched_n, len(items)),
            "missed_pct": _percentage(missed_n, len(items)),
        }

    # Sort by most frequently missed (most actionable for teachers)
    top_missed = sorted(
        [cf for cf in concept_frequency.values() if cf["missed_count"] > 0],
        key=lambda x: -x["missed_count"],
    )[:5]
    top_matched = sorted(
        [cf for cf in concept_frequency.values() if cf["matched_count"] > 0],
        key=lambda x: -x["matched_count"],
    )[:5]

    # Edge case analysis
    edge_case_counts = Counter(
        item.get("edge_case") for item in items if item.get("edge_case")
    )

    # Grade band distribution within this score band
    grade_band_dist = Counter(item.get("grade_band", "incorrect") for item in items)

    # Common misconceptions
    misconceptions = []
    if reject_counts:
        for signal, count in reject_counts.most_common(3):
            misconceptions.append({
                "signal": signal,
                "count": count,
                "percentage": _percentage(count, len(items)),
            })

    return {
        "top_missed_concepts": top_missed,
        "top_matched_concepts": top_matched,
        "misconceptions": misconceptions,
        "common_matched_keywords": [kw for kw, _ in keyword_counts.most_common(6)],
        "edge_cases": dict(edge_case_counts),
        "grade_band_distribution": dict(grade_band_dist),
        "concept_frequency": list(concept_frequency.values()),
    }


def _build_explanation(items: list[dict], band_label: str, band_kind: str, max_marks: float) -> str:
    """Build a human-readable explanation for a score band."""
    n = len(items)
    avg_score = _mean(items, "score")
    avg_sim = round(_mean(items, "similarity") * 100)

    missed = _join_top(
        [c for item in items for c in item.get("missed_concepts", [])],
        "no common gap",
    )
    matched = _join_top(
        [c for item in items for c in item.get("matched_concepts", [])],
        "limited shared reasoning",
    )

    if band_kind == "excellent":
        return (
            f"{n} student(s) scored excellently (avg {avg_score}/{max_marks}, "
            f"{avg_sim}% alignment). They consistently cover {matched}."
        )
    if band_kind == "good":
        return (
            f"{n} student(s) show good understanding (avg {avg_score}/{max_marks}, "
            f"{avg_sim}% alignment). They cover {matched} but sometimes miss {missed}."
        )
    if band_kind == "average":
        return (
            f"{n} student(s) show average understanding (avg {avg_score}/{max_marks}, "
            f"{avg_sim}% alignment). They partially cover {matched} and commonly miss {missed}."
        )
    return (
        f"{n} student(s) need improvement (avg {avg_score}/{max_marks}, "
        f"{avg_sim}% alignment). They commonly miss {missed}."
    )


def _build_common_pattern(items: list[dict], band_kind: str) -> str:
    """Generate a common pattern description for the band."""
    matched = _join_top(
        [c for item in items for c in item.get("matched_concepts", [])],
        "limited shared reasoning",
    )
    missed = _join_top(
        [c for item in items for c in item.get("missed_concepts", [])],
        "no repeated gap",
    )
    rejects = _join_top(
        [r for item in items for r in item.get("reject_hits", [])],
        "",
    )

    if band_kind == "excellent":
        return f"Students comprehensively cover {matched} with strong alignment to the reference answer."
    if band_kind == "good":
        return f"Students demonstrate solid understanding of {matched} with minor gaps in {missed}."
    if band_kind == "average":
        return f"Students partially grasp {matched} but frequently miss {missed}."
    # poor
    if rejects:
        return f"Students show misconceptions ({rejects}) and commonly miss {missed}."
    return f"Students struggle with core concepts and commonly miss {missed}."


def _build_teaching_recommendation(items: list[dict], band_kind: str) -> str:
    """Generate actionable teaching recommendations per band."""
    missed = _join_top(
        [c for item in items for c in item.get("missed_concepts", [])],
        "core concepts",
    )
    rejects = _join_top(
        [r for item in items for r in item.get("reject_hits", [])],
        "",
    )

    if band_kind == "excellent":
        return "These students have mastered the content. Consider challenging them with extension questions."
    if band_kind == "good":
        return f"Focus revision on bridging the gap in: {missed}. These students are close to full marks."
    if band_kind == "average":
        return f"Targeted review needed on: {missed}. Consider worked examples and practice problems."
    if rejects:
        return f"Address the misconception: {rejects}. Re-teach foundational concepts: {missed}."
    return f"Re-teach the foundational concepts: {missed}. Consider one-on-one support for these students."


# ── Main Entry Point ────────────────────────────────────────────────────────

CATEGORY_PRIORITY = {
    "excellent": 0,
    "good": 1,
    "average": 2,
    "poor": 3,
}


def run_clustering_for_question(q_number: str, reference_data: dict, students_data: list) -> list:
    """
    Group student answers into score-based performance tiers for a given question.

    Students are bucketed by their score_ratio (score / max_marks):
      - 0.0–0.4  → Needs Improvement (Poor)
      - 0.4–0.7  → Average Understanding
      - 0.7–0.9  → Good Understanding
      - 0.9–1.0  → Excellent

    Within each tier, rich insights are extracted: common missed/matched concepts,
    misconceptions, keyword patterns, and teaching recommendations.
    """

    max_marks = float(reference_data.get("max_marks", 5.0))

    # ── Collect items ────────────────────────────────────────────────────
    items = []
    for student in students_data:
        score_data = student.get("scores", {}).get(q_number)
        if not score_data or not score_data.get("attempted"):
            continue

        items.append({
            "roll_number": student.get("roll_number", "Unknown"),
            "name": student.get("name", "Unknown"),
            "answer_text": score_data.get("student_answer_text", ""),
            "score": float(score_data.get("score", 0.0)),
            "score_ratio": float(score_data.get("score_ratio", 0.0)),
            "similarity": float(score_data.get("similarity", 0.0)),
            "concept_coverage": float(score_data.get("concept_coverage", 0.0)),
            "keyword_coverage": float(score_data.get("keyword_coverage", 0.0)),
            "structure_score": float(score_data.get("structure_score", 0.0)),
            "formula_score": float(score_data.get("formula_score", 0.0)),
            "numeric_score": float(score_data.get("numeric_score", 0.0)),
            "grading_confidence": float(score_data.get("grading_confidence", 0.0)),
            "grade_band": score_data.get("grade_band") or "incorrect",
            "edge_case": score_data.get("edge_case"),
            "matched_concepts": list(score_data.get("matched_concepts", [])),
            "missed_concepts": list(score_data.get("missed_concepts", [])),
            "matched_keywords": list(score_data.get("matched_keywords", [])),
            "matched_keyword_highlights": list(score_data.get("matched_keyword_highlights", [])),
            "reject_hits": list(score_data.get("reject_hits", [])),
        })

    if not items:
        return []

    # ── Bucket students into score bands ─────────────────────────────────
    bands: dict[str, list[dict]] = defaultdict(list)
    band_meta: dict[str, tuple[str, str]] = {}  # kind -> (label, color)

    for item in items:
        band_label, band_kind, band_color = _get_band(item["score_ratio"])
        bands[band_kind].append(item)
        band_meta[band_kind] = (band_label, band_color)

    # ── Build result list ────────────────────────────────────────────────
    results = []
    cluster_id = 0

    for band_kind in ["excellent", "good", "average", "poor"]:
        band_items = bands.get(band_kind)
        if not band_items:
            continue

        band_label, band_color = band_meta[band_kind]
        low, high = next(
            (lo, hi) for lo, hi, lbl, knd, _ in SCORE_BANDS if knd == band_kind
        )

        # Build public student list
        public_students = []
        for item in sorted(band_items, key=lambda row: (-row["score"], row["roll_number"])):
            public_students.append({
                "roll_number": item["roll_number"],
                "name": item["name"],
                "answer_text": item["answer_text"],
                "score": round(item["score"], 1),
                "score_ratio": round(item["score_ratio"], 4),
                "similarity": round(item["similarity"], 4),
                "concept_coverage": round(item["concept_coverage"], 4),
                "keyword_coverage": round(item["keyword_coverage"], 4),
                "structure_score": round(item["structure_score"], 4),
                "formula_score": round(item["formula_score"], 4),
                "numeric_score": round(item["numeric_score"], 4),
                "grading_confidence": round(item["grading_confidence"], 4),
                "grade_band": item["grade_band"],
                "edge_case": item["edge_case"],
                "matched_concepts": item["matched_concepts"],
                "missed_concepts": item["missed_concepts"],
                "matched_keywords": item["matched_keywords"],
                "matched_keyword_highlights": item["matched_keyword_highlights"],
            })

        insights = _extract_insights(band_items, band_label, band_kind)
        explanation = _build_explanation(band_items, band_label, band_kind, max_marks)
        pattern = _build_common_pattern(band_items, band_kind)
        recommendation = _build_teaching_recommendation(band_items, band_kind)

        results.append({
            # Core identity
            "cluster_id": str(cluster_id),
            "cluster_name": f"{band_label} ({len(band_items)} students)",
            "label": band_label,

            # Band metadata
            "cluster_kind": band_kind,
            "band_kind": band_kind,
            "band_label": band_label,
            "band_color": band_color,
            "score_range": {
                "min_ratio": low,
                "max_ratio": high,
                "min_score": round(low * max_marks, 1),
                "max_score": round(min(high, 1.0) * max_marks, 1),
            },
            "is_outlier": False,

            # Backward-compat fields — grade_band must be a string for the frontend
            "grade_band": band_kind,
            "grade_band_distribution": insights["grade_band_distribution"],
            "dbscan_label": cluster_id,
            "dbscan_eps": 0.0,
            "dbscan_min_samples": 0,

            # Aggregate stats
            "student_count": len(public_students),
            "avg_score": _mean(band_items, "score"),
            "avg_similarity": _mean(band_items, "similarity"),
            "avg_confidence": _mean(band_items, "grading_confidence"),
            "avg_concept_coverage": _mean(band_items, "concept_coverage"),
            "avg_keyword_coverage": _mean(band_items, "keyword_coverage"),
            "avg_structure_score": _mean(band_items, "structure_score"),

            # Rich insights
            "common_pattern": pattern,
            "explanation": explanation,
            "insight": explanation,
            "teaching_recommendation": recommendation,
            "insights": insights,

            # Students
            "students": public_students,
        })

        cluster_id += 1

    # Sort by band priority (excellent first, poor last)
    results.sort(key=lambda c: CATEGORY_PRIORITY.get(c.get("cluster_kind"), 99))

    return results
