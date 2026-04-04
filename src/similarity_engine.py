"""
Embedding, rubric, and grading helpers for reference-answer evaluation.
"""
import os
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

_CACHE_ROOT = Path(__file__).resolve().parent.parent / ".hf_cache"
os.environ.setdefault("HF_HOME", str(_CACHE_ROOT))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(_CACHE_ROOT))
os.environ.setdefault("TRANSFORMERS_CACHE", str(_CACHE_ROOT))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_CACHE_ROOT / "hub"))

EMBED_MODEL = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

_embedder = None

EN_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below", "between",
    "both", "but", "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each",
    "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of",
    "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself",
    "yourselves",
}

HINGLISH_STOPWORDS = {
    "aur", "bhi", "hai", "hain", "ka", "ke", "ki", "ko", "me", "mein", "par", "se", "tak", "ya",
    "ye", "yah", "wo", "vah", "ek", "is", "us", "jo", "kiya", "karna", "karte", "karne", "hota",
    "hoti", "hote",
}

DEVANAGARI_STOPWORDS = {
    "और", "का", "के", "की", "को", "में", "पर", "से", "तक", "यह", "वह", "एक", "है", "हैं", "था",
    "थे", "थी", "जो", "किया", "करना", "करते", "करने",
}

STOPWORDS = EN_STOPWORDS | HINGLISH_STOPWORDS | DEVANAGARI_STOPWORDS
GENERIC_KEYWORDS = {
    "answer", "question", "explain", "define", "steps", "step", "process", "pipeline", "method",
    "data", "student", "teacher", "example",
}

PROCESS_HINTS = {
    "algorithm", "approach", "cycle", "flow", "lifecycle", "method", "pipeline", "procedure",
    "process", "stage", "step", "steps", "workflow",
}

RELATION_PATTERNS = {
    "definition": [
        r"\bstrength and direction\b",
        r"\bmeasure of the relationship\b",
        r"\brelationship between two variables\b",
    ],
    "positive": [
        r"\bpositive correlation\b",
        r"\bdirect relationship\b",
        r"\bsame direction\b",
        r"\bboth (?:variables\s+)?increase(?:s|d)?(?:\s+\w+){0,4}\s+together\b",
        r"\bboth (?:variables\s+)?decrease(?:s|d)?(?:\s+\w+){0,4}\s+together\b",
        r"\bone (?:variable\s+)?increase(?:s|d)?(?:\s+\w+){0,4}\bother (?:variable\s+)?increase(?:s|d)?\b",
        r"\bone (?:variable\s+)?decrease(?:s|d)?(?:\s+\w+){0,4}\bother (?:variable\s+)?decrease(?:s|d)?\b",
    ],
    "negative": [
        r"\bnegative correlation\b",
        r"\binverse relationship\b",
        r"\bopposite direction\b",
        r"\bone (?:variable\s+)?increase(?:s|d)?(?:\s+\w+){0,5}\bother (?:variable\s+)?decrease(?:s|d)?\b",
        r"\bone (?:variable\s+)?decrease(?:s|d)?(?:\s+\w+){0,5}\bother (?:variable\s+)?increase(?:s|d)?\b",
    ],
    "zero": [
        r"\bzero correlation\b",
        r"\bno linear relationship\b",
        r"\bno relationship\b",
        r"\bno relation\b",
        r"\buncorrelated\b",
        r"\bindependent\b",
    ],
    "equality": [
        r"\balways equal\b",
        r"\bexactly equal\b",
        r"\bequal always\b",
        r"\bsame value always\b",
    ],
    "constant": [
        r"\bstays constant\b",
        r"\bremains constant\b",
        r"\bconstant while\b",
        r"\bone increases?(?:\s+\w+){0,4}\bother stays constant\b",
        r"\bone decreases?(?:\s+\w+){0,4}\bother stays constant\b",
    ],
}

RELATION_CONTRADICTIONS = {
    "positive": {"negative", "zero", "equality", "constant"},
    "negative": {"positive", "zero", "equality", "constant"},
    "zero": {"positive", "negative", "equality"},
    "definition": {"equality", "constant"},
}


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def encode_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0))
    return get_embedder().encode(texts, normalize_embeddings=True)


def normalize_question_id(raw: str | None) -> str | None:
    if not raw:
        return None

    value = str(raw).strip().upper()
    if not value:
        return None

    match = re.search(r"(?:Q|QUESTION)\s*([0-9]+[A-Z]?)", value)
    if match:
        return f"Q{match.group(1)}"

    match = re.search(r"\b([0-9]+[A-Z]?)\b", value)
    if match:
        return f"Q{match.group(1)}"

    compact = re.sub(r"[^A-Z0-9]+", "", value)
    return compact or None


def question_sort_key(q_number: str) -> tuple[int, str]:
    normalized = normalize_question_id(q_number) or q_number
    match = re.match(r"Q([0-9]+)([A-Z]?)", normalized)
    if match:
        return (int(match.group(1)), match.group(2))
    return (10**9, normalized)


def make_combined_text(answer: dict) -> str:
    q_text = (answer.get("q_text") or "").strip()
    text = (answer.get("text") or "").strip()
    diag = (answer.get("diagram_description") or "").strip()

    parts = []
    if q_text:
        parts.append(f"[Question]: {q_text}")
    if text:
        parts.append(f"[Answer]: {text}")
    if diag and diag.lower() not in {"none", "null"}:
        parts.append(f"[Diagram]: {diag}")

    return " | ".join(parts).strip()


def make_answer_text(answer: dict) -> str:
    text = (answer.get("text") or "").strip()
    diag = (answer.get("diagram_description") or "").strip()
    parts = []
    if text:
        parts.append(text)
    if diag and diag.lower() not in {"none", "null"}:
        parts.append(f"Diagram: {diag}")
    return "\n".join(parts).strip()


def merge_answer_records(records: Iterable[dict], include_max_marks: bool = False) -> list[dict]:
    merged: dict[str, dict] = {}
    order: list[str] = []

    for record in records:
        q_number = normalize_question_id(record.get("q_number"))
        if not q_number:
            continue

        if q_number not in merged:
            merged[q_number] = {
                "q_number": q_number,
                "q_text": (record.get("q_text") or "").strip() or None,
                "text": (record.get("text") or "").strip(),
                "diagram_present": bool(record.get("diagram_present")),
                "diagram_description": (record.get("diagram_description") or "").strip() or None,
                "attempted": bool(record.get("attempted", True)),
                "source_pages": list(record.get("source_pages", []) or []),
            }
            if include_max_marks:
                max_marks = record.get("max_marks")
                merged[q_number]["max_marks"] = float(max_marks) if max_marks is not None else None
            order.append(q_number)
            continue

        current = merged[q_number]
        new_text = (record.get("text") or "").strip()
        if new_text and new_text not in current["text"]:
            current["text"] = f"{current['text']}\n{new_text}".strip()

        q_text = (record.get("q_text") or "").strip()
        if q_text and (not current.get("q_text") or len(q_text) > len(current["q_text"])):
            current["q_text"] = q_text

        diagram_description = (record.get("diagram_description") or "").strip()
        if diagram_description:
            current["diagram_present"] = True
            if current.get("diagram_description"):
                if diagram_description not in current["diagram_description"]:
                    current["diagram_description"] = (
                        f"{current['diagram_description']}\n{diagram_description}"
                    ).strip()
            else:
                current["diagram_description"] = diagram_description

        current["attempted"] = current["attempted"] or bool(record.get("attempted", True))
        incoming_pages = [page for page in (record.get("source_pages", []) or []) if page not in current["source_pages"]]
        if incoming_pages:
            current["source_pages"].extend(incoming_pages)

        if include_max_marks:
            existing = current.get("max_marks")
            incoming = record.get("max_marks")
            if incoming is not None:
                incoming = float(incoming)
                current["max_marks"] = max(existing or 0.0, incoming) if existing is not None else incoming

    return [merged[q_number] for q_number in order]


def cosine_similarity_score(student_embedding: np.ndarray, reference_embedding: np.ndarray) -> float:
    return float(np.clip(np.dot(student_embedding, reference_embedding), -1.0, 1.0))


def similarity_to_score(similarity: float, max_marks: float) -> float:
    scaled = max(0.0, min(1.0, similarity))
    return round(scaled * max_marks, 1)


def _normalize_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _canonical_match_text(text: str | None) -> str:
    normalized = _normalize_text(text)
    normalized = normalized.replace("–", "-").replace("—", "-").replace("−", "-")
    normalized = normalized.replace("→", " ").replace("↓", " ")
    normalized = re.sub(r"[^0-9a-z\u0900-\u097f]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z\u0900-\u097F]+", _normalize_text(text))


def _token_overlap_ratio(reference_tokens: list[str], student_tokens: list[str]) -> float:
    if not reference_tokens or not student_tokens:
        return 0.0

    reference_counts = Counter(reference_tokens)
    student_counts = Counter(student_tokens)
    shared = sum(min(reference_counts[token], student_counts[token]) for token in reference_counts)
    total = max(sum(reference_counts.values()), sum(student_counts.values()))
    if total <= 0:
        return 0.0
    return float(shared / total)


def _stem_token(token: str) -> str:
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return token
    for suffix in ("tion", "ment", "ness", "ingly", "edly", "ingly", "ings", "edly", "ing", "ers", "ies", "ied", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            if suffix in {"ies", "ied"}:
                return token[:-3] + "y"
            return token[: -len(suffix)]
    return token


def _is_content_token(token: str) -> bool:
    return len(token) > 2 and token not in STOPWORDS and token not in GENERIC_KEYWORDS and not token.isdigit()


def _split_segments(text: str) -> list[str]:
    cleaned = (text or "").replace("\r", "\n")
    cleaned = re.sub(r"[•●▪◦]", "\n", cleaned)
    cleaned = re.sub(r"\s+(?=\d+[\).\:-]\s+)", "\n", cleaned)
    cleaned = re.sub(r"(?m)^\s*(?:step\s*)?\d+[\).\:-]\s*", "", cleaned)
    parts = re.split(r"\n+|(?<=[.!?;])\s+", cleaned)
    segments: list[str] = []
    seen: set[str] = set()
    for part in parts:
        segment = part.strip(" -:;,.")
        if len(_tokenize(segment)) < 3:
            continue
        key = _normalize_text(segment)
        if key and key not in seen:
            segments.append(segment)
            seen.add(key)
    if not segments and cleaned.strip():
        segments = [cleaned.strip()]
    return segments[:10]


def _extract_keywords(text: str, limit: int = 10) -> list[str]:
    tokens = [_stem_token(token) for token in _tokenize(text) if _is_content_token(token)]
    counts = Counter(tokens)
    keywords = [token for token, _ in counts.most_common(limit * 2)]
    filtered: list[str] = []
    for token in keywords:
        if token in filtered:
            continue
        filtered.append(token)
        if len(filtered) >= limit:
            break
    return filtered


def _normalize_rubric_items(question: dict) -> list[dict]:
    rubric = question.get("llm_rubric") or {}
    items = question.get("rubric_items") or rubric.get("concepts") or []
    normalized = []
    for index, item in enumerate(items, start=1):
        description = str(item.get("description") or item.get("concept") or "").strip()
        if not description:
            continue
        weight = item.get("weight")
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            weight = 1.0
        keywords = [str(keyword).strip().lower() for keyword in item.get("keywords", []) if str(keyword).strip()]
        normalized.append({
            "id": str(item.get("id") or f"C{index}").strip() or f"C{index}",
            "description": description,
            "weight": max(weight, 0.0),
            "keywords": keywords[:6],
            "type": str(item.get("type") or "core").strip().lower() or "core",
        })

    if not normalized:
        return []

    total = sum(item["weight"] for item in normalized) or float(len(normalized))
    for item in normalized:
        item["weight"] = round(item["weight"] / total, 4)
    return normalized


def _concept_keywords(text: str, limit: int = 4) -> list[str]:
    keywords = []
    for token in _tokenize(text):
        stemmed = _stem_token(token)
        if not _is_content_token(stemmed):
            continue
        if stemmed not in keywords:
            keywords.append(stemmed)
        if len(keywords) >= limit:
            break
    return keywords


def _expects_steps(question_text: str, reference_text: str, segments: list[str]) -> bool:
    combined = _normalize_text(f"{question_text} {reference_text}")
    return len(segments) >= 4 or any(hint in combined for hint in PROCESS_HINTS)


def _scale_similarity(value: float, low: float = 0.18, high: float = 0.78) -> float:
    if high <= low:
        return max(0.0, min(1.0, value))
    return float(max(0.0, min(1.0, (value - low) / (high - low))))


def _length_factor(student_tokens: int, reference_tokens: int) -> float:
    if student_tokens <= 0 or reference_tokens <= 0:
        return 0.0
    target = max(5, int(reference_tokens * 0.35))
    return float(max(0.0, min(1.0, student_tokens / target)))


def _relation_tags(text: str) -> set[str]:
    normalized = _normalize_text(text)
    tags: set[str] = set()
    for tag, patterns in RELATION_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            tags.add(tag)
    return tags


def _concept_contradictions(concept_text: str, matched_excerpt: str | None, student_text: str) -> list[str]:
    expected_tags = _relation_tags(concept_text)
    if not expected_tags:
        return []

    evidence = matched_excerpt or student_text
    actual_tags = _relation_tags(evidence)
    if not actual_tags:
        return []

    contradictions: list[str] = []
    for expected_tag, conflicting_tags in RELATION_CONTRADICTIONS.items():
        if expected_tag not in expected_tags:
            continue
        for conflicting_tag in sorted(actual_tags & conflicting_tags):
            contradictions.append(f"{expected_tag}_vs_{conflicting_tag}")
    return contradictions


def _extract_formula_candidates(text: str) -> list[str]:
    candidates = []
    for chunk in re.split(r"[\n;,.]", text or ""):
        normalized = chunk.strip()
        if not normalized:
            continue
        if re.search(r"[=+\-*/^]", normalized) and re.search(r"\d", normalized):
            candidates.append(normalized)
    return candidates


def _extract_equation_templates(text: str) -> list[str]:
    templates = []
    for chunk in re.split(r"[\n;,.]", text or ""):
        normalized = chunk.strip()
        if not normalized or "=" not in normalized:
            continue
        matches = re.findall(r"[A-Za-z][A-Za-z0-9]*\s*=\s*[A-Za-z0-9\s*+\-/^()]+", normalized)
        for match in matches:
            templates.append(match.strip())
    return templates


def _formula_signature(text: str) -> str:
    normalized = _normalize_text(text).replace("x", "*")
    normalized = normalized.replace(" ", "")
    normalized = re.sub(r"\d+(?:\.\d+)?", "#", normalized)
    normalized = re.sub(r"[a-z\u0900-\u097f]+", "v", normalized)
    normalized = re.sub(r"[^#v=+\-*/^()]", "", normalized)
    return normalized


def _formula_structure(signature: str) -> str:
    return re.sub(r"#+", "", signature)


def _formula_presence_score(student_text: str, reference_question: dict) -> float:
    formula_expected = str(reference_question.get("formula_expected") or "").strip()
    if not formula_expected:
        return 0.0

    expected_signature = _formula_structure(_formula_signature(formula_expected))
    if not expected_signature:
        return 0.0

    student_equations = _extract_equation_templates(student_text)
    if not student_equations:
        return 0.0

    student_signatures = {
        _formula_structure(_formula_signature(equation))
        for equation in student_equations
        if equation.strip()
    }
    if expected_signature in student_signatures:
        return 1.0
    if any(expected_signature in signature or signature in expected_signature for signature in student_signatures if signature):
        return 0.75
    return 0.0


def _numeric_correctness_score(student_text: str, reference_question: dict) -> float:
    expected = str(reference_question.get("final_numeric_answer") or "").strip()
    if not expected:
        return 0.0

    expected_numbers = re.findall(r"-?\d+(?:\.\d+)?", expected)
    student_numbers = re.findall(r"-?\d+(?:\.\d+)?", student_text or "")
    if not expected_numbers or not student_numbers:
        return 0.0

    expected_final = expected_numbers[-1]
    if expected_final == student_numbers[-1]:
        return 1.0
    if expected_final in student_numbers:
        return 0.4
    return 0.0


def _structure_score(
    student_text: str,
    rubric_concepts: list[dict],
    expects_steps: bool,
    formula_score: float,
    numeric_score: float,
) -> float:
    matched_indexes = [index for index, concept in enumerate(rubric_concepts) if concept.get("status") == "matched"]
    partial_indexes = [index for index, concept in enumerate(rubric_concepts) if concept.get("status") == "partial"]

    if len(matched_indexes) <= 1:
        order_score = 1.0 if matched_indexes else 0.0
    else:
        ordered_pairs = sum(1 for first, second in zip(matched_indexes, matched_indexes[1:]) if second > first)
        order_score = ordered_pairs / max(1, len(matched_indexes) - 1)

    step_marker_present = bool(
        re.search(r"^\s*\d+[\).\:-]|\b(first|second|third|next|then|finally|step)\b", student_text or "", flags=re.IGNORECASE | re.MULTILINE)
    )
    concept_progress = (len(matched_indexes) + 0.5 * len(partial_indexes)) / max(1, len(rubric_concepts))

    structure = 0.45 * concept_progress + 0.35 * order_score + 0.2 * (1.0 if step_marker_present or not expects_steps else 0.0)
    if formula_score < 0.5:
        structure *= 0.9
    if numeric_score == 0.0 and formula_score > 0.0:
        structure *= 0.92
    return float(max(0.0, min(1.0, structure)))


def _keyword_highlights(text: str, keywords: list[str]) -> list[dict]:
    if not text:
        return []

    highlights = []
    lowered = text.lower()
    seen = set()
    for keyword in keywords:
        token = str(keyword or "").strip().lower()
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        start = lowered.find(token)
        if start >= 0:
            highlights.append({
                "term": keyword,
                "start": start,
                "end": start + len(token),
            })
    highlights.sort(key=lambda entry: (entry["start"], entry["end"]))
    return highlights[:12]


def _detect_formula_edge_case(student_text: str, reference_text: str, question_text: str) -> dict | None:
    combined = _normalize_text(f"{question_text} {reference_text}")
    if not any(term in combined for term in {"calculate", "compute", "determine", "evaluate", "find", "solve"}):
        if not _extract_formula_candidates(reference_text):
            return None

    reference_candidates = _extract_formula_candidates(reference_text)
    student_candidates = _extract_formula_candidates(student_text)
    if not reference_candidates or not student_candidates:
        return None

    reference_templates = {
        _formula_structure(_formula_signature(template))
        for template in _extract_equation_templates(reference_text)
    }
    student_templates = {
        _formula_structure(_formula_signature(template))
        for template in _extract_equation_templates(student_text)
    }

    reference_signatures = {_formula_signature(candidate) for candidate in reference_candidates}
    student_signatures = {_formula_signature(candidate) for candidate in student_candidates}
    reference_structures = {_formula_structure(signature) for signature in reference_signatures if signature}
    student_structures = {_formula_structure(signature) for signature in student_signatures if signature}

    shared = [signature for signature in student_signatures if signature and signature in reference_signatures]
    if not shared:
        for template in student_templates:
            for reference_template in reference_templates:
                if template and reference_template and (
                    template == reference_template
                    or template in reference_template
                    or reference_template in template
                ):
                    shared.append(template)
                    break
    if not shared:
        for student_structure in student_structures:
            for reference_structure in reference_structures:
                if student_structure and reference_structure and (
                    student_structure == reference_structure
                    or student_structure in reference_structure
                    or reference_structure in student_structure
                ):
                    shared.append(student_structure)
                    break
    if not shared:
        return None

    reference_numbers = re.findall(r"-?\d+(?:\.\d+)?", reference_text or "")
    student_numbers = re.findall(r"-?\d+(?:\.\d+)?", student_text or "")
    if not reference_numbers or not student_numbers:
        return None

    if reference_numbers[-1] == student_numbers[-1]:
        return None

    return {
        "type": "formula_correct_calculation_wrong",
        "confidence": round(min(1.0, 0.55 + 0.15 * len(shared)), 2),
    }


def build_reference_profile(question: dict) -> dict:
    answer_text = make_answer_text(question)
    rubric_items = _normalize_rubric_items(question)
    segments = [item["description"] for item in rubric_items] if rubric_items else _split_segments(answer_text)
    segment_embeddings = encode_texts(segments) if segments else np.empty((0, 0))
    if rubric_items:
        keywords = []
        for item in rubric_items:
            keywords.extend(item.get("keywords", []))
        for alternate in question.get("llm_rubric", {}).get("accept_alternates", []):
            keywords.extend(_extract_keywords(str(alternate), limit=4))
        keywords = list(dict.fromkeys([keyword for keyword in keywords if keyword]))[:12]
        if not keywords:
            keywords = _extract_keywords(answer_text)
        rubric_weights = [item["weight"] for item in rubric_items]
        rubric_concept_ids = [item["id"] for item in rubric_items]
    else:
        keywords = _extract_keywords(answer_text)
        uniform_weight = round(1.0 / len(segments), 4) if segments else 0.0
        rubric_weights = [uniform_weight for _ in segments]
        rubric_concept_ids = [f"C{index + 1}" for index in range(len(segments))]

    return {
        "answer_text": answer_text,
        "rubric_items": rubric_items,
        "rubric_segments": segments,
        "rubric_segment_embeddings": segment_embeddings,
        "rubric_keywords": keywords,
        "rubric_weights": rubric_weights,
        "rubric_concept_ids": rubric_concept_ids,
        "expects_steps": bool(question.get("llm_rubric", {}).get("requires_steps")) or _expects_steps(question.get("q_text", ""), answer_text, segments),
        "reject_signals": question.get("llm_rubric", {}).get("reject_signals", []),
        "accept_alternates": question.get("llm_rubric", {}).get("accept_alternates", []),
        "formula_expected": question.get("llm_rubric", {}).get("formula_expected"),
        "final_numeric_answer": question.get("llm_rubric", {}).get("final_numeric_answer"),
        "diagram_expected": bool(question.get("llm_rubric", {}).get("diagram_expected")),
    }


def _exact_match_grade(student_text: str, reference_question: dict) -> dict | None:
    reference_text = reference_question.get("answer_text") or make_answer_text(reference_question)
    canonical_reference = _canonical_match_text(reference_text)
    canonical_student = _canonical_match_text(student_text)
    if not canonical_reference or not canonical_student:
        return None

    reference_tokens = canonical_reference.split()
    student_tokens = canonical_student.split()
    sequence_ratio = SequenceMatcher(None, canonical_reference, canonical_student).ratio()
    token_overlap = _token_overlap_ratio(reference_tokens, student_tokens)
    length_ratio = min(len(student_tokens), len(reference_tokens)) / max(1, max(len(student_tokens), len(reference_tokens)))
    containment = (
        canonical_student in canonical_reference
        or canonical_reference in canonical_student
    )

    is_exact_match = canonical_reference == canonical_student
    is_near_exact_match = (
        sequence_ratio >= 0.985 and token_overlap >= 0.97 and length_ratio >= 0.93
    ) or (
        containment and token_overlap >= 0.985 and length_ratio >= 0.97
    )
    if not (is_exact_match or is_near_exact_match):
        return None

    rubric_segments = reference_question.get("rubric_segments") or _split_segments(reference_text)
    rubric_concept_ids = reference_question.get("rubric_concept_ids") or [f"C{index + 1}" for index in range(len(rubric_segments))]
    rubric_weights = reference_question.get("rubric_weights") or (
        [round(1.0 / len(rubric_segments), 4) for _ in rubric_segments] if rubric_segments else []
    )
    rubric_concepts = [
        {
            "id": rubric_concept_ids[index] if index < len(rubric_concept_ids) else f"C{index + 1}",
            "concept": concept,
            "status": "matched",
            "match_score": 1.0,
            "coverage": 1.0,
            "weight": rubric_weights[index] if index < len(rubric_weights) else 0.0,
            "matched_excerpt": student_text[:400] if student_text else None,
            "contradiction_hits": [],
        }
        for index, concept in enumerate(rubric_segments)
    ]

    reference_keywords = reference_question.get("rubric_keywords") or _extract_keywords(reference_text)
    return {
        "score": round(reference_question["max_marks"], 1),
        "similarity": 1.0,
        "raw_similarity": 1.0,
        "concept_coverage": 1.0,
        "keyword_coverage": 1.0 if reference_keywords else 1.0,
        "structure_score": 1.0,
        "formula_score": 1.0 if str(reference_question.get("formula_expected") or "").strip() else 0.0,
        "numeric_score": 1.0 if str(reference_question.get("final_numeric_answer") or "").strip() else 0.0,
        "strong_concept_ratio": 1.0,
        "matched_keywords": reference_keywords,
        "matched_keyword_highlights": _keyword_highlights(student_text, reference_keywords),
        "missing_keywords": [],
        "rubric_concepts": rubric_concepts,
        "matched_concepts": [entry["concept"] for entry in rubric_concepts],
        "matched_concept_ids": [entry["id"] for entry in rubric_concepts],
        "missed_concepts": [],
        "missed_concept_ids": [],
        "grade_band": "correct",
        "edge_case": None,
        "edge_case_confidence": 0.0,
        "score_ratio": 1.0,
        "semantic_signal": 1.0,
        "grading_confidence": 0.99,
        "feedback_summary": "Answer matches the reference answer closely enough to award full credit.",
        "reject_hits": [],
        "contradiction_hits": [],
        "contradiction_count": 0,
        "grading_method": "exact_match",
    }


def grade_answer(student_answer: dict, reference_question: dict, student_embedding: np.ndarray) -> dict:
    reference_text = reference_question.get("answer_text") or make_answer_text(reference_question)
    student_text = make_answer_text(student_answer)
    if not student_text:
        return {
            "score": 0.0,
            "similarity": 0.0,
            "concept_coverage": 0.0,
            "keyword_coverage": 0.0,
            "structure_score": 0.0,
            "formula_score": 0.0,
            "numeric_score": 0.0,
            "matched_keywords": [],
            "matched_keyword_highlights": [],
            "missing_keywords": reference_question.get("rubric_keywords", []),
            "rubric_concepts": [],
            "matched_concepts": [],
            "missed_concepts": reference_question.get("rubric_segments", []),
            "grade_band": "incorrect",
            "edge_case": None,
            "edge_case_confidence": 0.0,
            "score_ratio": 0.0,
            "semantic_signal": 0.0,
            "grading_confidence": 0.0,
            "feedback_summary": "No answer extracted for this question.",
            "grading_method": "deterministic",
            "answer_embedding_vector": student_embedding.tolist(),
        }

    exact_match_grade = _exact_match_grade(student_text, reference_question)
    if exact_match_grade is not None:
        exact_match_grade["answer_embedding_vector"] = student_embedding.tolist()
        return exact_match_grade

    reference_embedding = reference_question.get("answer_embedding")
    if reference_embedding is None:
        reference_embedding = encode_texts([reference_text])[0]

    global_similarity = cosine_similarity_score(student_embedding, reference_embedding)
    global_similarity_scaled = _scale_similarity(global_similarity, low=0.15, high=0.75)

    rubric_segments = reference_question.get("rubric_segments") or _split_segments(reference_text)
    rubric_segment_embeddings = reference_question.get("rubric_segment_embeddings")
    if rubric_segments and (rubric_segment_embeddings is None or getattr(rubric_segment_embeddings, "size", 0) == 0):
        rubric_segment_embeddings = encode_texts(rubric_segments)
    rubric_items = reference_question.get("rubric_items") or []
    rubric_weights = reference_question.get("rubric_weights") or []
    if not rubric_weights and rubric_segments:
        rubric_weights = [1.0 / len(rubric_segments) for _ in rubric_segments]
    rubric_concept_ids = reference_question.get("rubric_concept_ids") or [f"C{index + 1}" for index in range(len(rubric_segments))]

    student_segments = _split_segments(student_text)
    student_segment_embeddings = encode_texts(student_segments) if student_segments else np.empty((0, 0))
    student_tokens = {_stem_token(token) for token in _tokenize(student_text)}
    student_content_tokens = {token for token in student_tokens if _is_content_token(token)}
    student_text_normalized = _normalize_text(student_text)

    rubric_concepts = []
    weighted_concept_scores: list[float] = []
    strong_matches = 0
    contradiction_hits: list[str] = []
    for index, concept in enumerate(rubric_segments):
        best_similarity = 0.0
        best_excerpt = None
        if student_segments and getattr(student_segment_embeddings, "size", 0) > 0:
            similarities = np.dot(student_segment_embeddings, rubric_segment_embeddings[index])
            best_index = int(np.argmax(similarities))
            best_similarity = float(np.clip(similarities[best_index], -1.0, 1.0))
            best_excerpt = student_segments[best_index]

        concept_keywords = rubric_items[index]["keywords"] if index < len(rubric_items) and rubric_items[index].get("keywords") else _concept_keywords(concept)
        keyword_hits = sum(1 for keyword in concept_keywords if keyword in student_content_tokens)
        target_keyword_hits = max(1, min(2, len(concept_keywords)))
        lexical_coverage = float(min(1.0, keyword_hits / target_keyword_hits)) if concept_keywords else 0.0
        semantic_component = _scale_similarity(best_similarity, low=0.25, high=0.78)
        coverage_value = 0.72 * semantic_component + 0.28 * lexical_coverage
        if semantic_component < 0.15:
            coverage_value = min(coverage_value, lexical_coverage * 0.55)
        elif lexical_coverage >= 0.4:
            coverage_value = max(coverage_value, 0.65 * semantic_component + 0.35 * lexical_coverage)

        concept_contradictions = _concept_contradictions(concept, best_excerpt, student_text)
        if concept_contradictions:
            contradiction_hits.extend(
                [f"{rubric_concept_ids[index] if index < len(rubric_concept_ids) else f'C{index + 1}'}:{hit}" for hit in concept_contradictions]
            )
            coverage_value *= 0.12

        concept_weight = rubric_weights[index] if index < len(rubric_weights) else (1.0 / len(rubric_segments) if rubric_segments else 0.0)
        weighted_concept_scores.append(coverage_value * concept_weight)
        if coverage_value >= 0.55 and not concept_contradictions:
            strong_matches += 1

        if concept_contradictions:
            status = "missed"
        elif coverage_value >= 0.55 and semantic_component >= 0.35:
            status = "matched"
        elif coverage_value >= 0.25 and semantic_component >= 0.1:
            status = "partial"
        else:
            status = "missed"

        rubric_concepts.append({
            "id": rubric_concept_ids[index] if index < len(rubric_concept_ids) else f"C{index + 1}",
            "concept": concept,
            "status": status,
            "match_score": round(best_similarity, 4),
            "coverage": round(coverage_value, 4),
            "weight": round(concept_weight, 4),
            "matched_excerpt": best_excerpt,
            "contradiction_hits": concept_contradictions,
        })

    concept_coverage = float(sum(weighted_concept_scores)) if weighted_concept_scores else global_similarity_scaled
    strong_ratio = float(strong_matches / len(rubric_segments)) if rubric_segments else global_similarity_scaled
    contradiction_count = len(contradiction_hits)

    reference_keywords = reference_question.get("rubric_keywords") or _extract_keywords(reference_text)
    matched_keywords = [keyword for keyword in reference_keywords if keyword in student_tokens]
    missing_keywords = [keyword for keyword in reference_keywords if keyword not in student_tokens]
    keyword_coverage = float(len(matched_keywords) / len(reference_keywords)) if reference_keywords else concept_coverage
    keyword_highlights = _keyword_highlights(student_text, matched_keywords)

    reject_signals = [str(signal).strip().lower() for signal in reference_question.get("reject_signals", []) if str(signal).strip()]
    reject_hits = [signal for signal in reject_signals if signal in student_text_normalized]
    reject_penalty = min(0.48, 0.14 * len(reject_hits))

    student_token_count = len(_tokenize(student_text))
    reference_token_count = len(_tokenize(reference_text))
    length_factor = _length_factor(student_token_count, reference_token_count)
    formula_applicable = bool(str(reference_question.get("formula_expected") or "").strip())
    numeric_applicable = bool(str(reference_question.get("final_numeric_answer") or "").strip())
    formula_score = _formula_presence_score(student_text, reference_question) if formula_applicable else 0.0
    numeric_score = _numeric_correctness_score(student_text, reference_question) if numeric_applicable else 0.0
    structure_score = _structure_score(
        student_text,
        rubric_concepts,
        reference_question.get("expects_steps", False),
        formula_score if formula_applicable else 1.0,
        numeric_score if numeric_applicable else 1.0,
    )

    quality_ratio = (
        0.32 * global_similarity_scaled
        + 0.15 * keyword_coverage
        + 0.33 * concept_coverage
        + 0.20 * structure_score
    )
    if formula_applicable:
        quality_ratio = 0.90 * quality_ratio + 0.10 * formula_score
    if numeric_applicable:
        quality_ratio = 0.92 * quality_ratio + 0.08 * numeric_score

    if reference_question.get("expects_steps"):
        coverage_floor = min(1.0, strong_ratio / 0.45) if strong_ratio < 0.45 else 1.0
        quality_ratio *= 0.55 + 0.45 * coverage_floor

    if concept_coverage < 0.15 and global_similarity_scaled < 0.2:
        quality_ratio *= 0.6

    if student_token_count < 3:
        quality_ratio *= 0.5

    if reject_penalty:
        quality_ratio *= max(0.2, 1.0 - reject_penalty)

    if global_similarity_scaled >= 0.85 and concept_coverage < 0.2 and keyword_coverage < 0.1:
        quality_ratio *= 0.65
    if keyword_coverage >= 0.65 and concept_coverage < 0.2:
        quality_ratio *= 0.6
    if formula_applicable and formula_score == 0.0:
        quality_ratio *= 0.8
    if numeric_applicable and numeric_score == 0.0:
        quality_ratio *= 0.88

    if contradiction_count:
        contradiction_penalty = min(0.72, 0.22 * contradiction_count)
        quality_ratio *= max(0.08, 1.0 - contradiction_penalty)
        quality_ratio = min(quality_ratio, 0.58 if contradiction_count == 1 else 0.34)
    if contradiction_count and reject_hits:
        quality_ratio = min(quality_ratio, 0.28)

    edge_case = _detect_formula_edge_case(student_text, reference_text, reference_question.get("q_text", ""))
    edge_case_type = edge_case["type"] if edge_case else None
    edge_case_confidence = float(edge_case["confidence"]) if edge_case else 0.0
    if edge_case_type == "formula_correct_calculation_wrong":
        quality_ratio = min(0.65, max(quality_ratio, 0.45))

    quality_ratio = float(max(0.0, min(1.0, quality_ratio)))

    display_similarity = (
        0.45 * global_similarity_scaled
        + 0.35 * concept_coverage
        + 0.2 * structure_score
    )
    if reject_hits:
        display_similarity *= max(0.2, 1.0 - 0.18 * len(reject_hits))
    if contradiction_count:
        display_similarity *= max(0.1, 1.0 - 0.22 * contradiction_count)
    display_similarity = float(max(0.0, min(1.0, display_similarity)))

    if edge_case_type == "formula_correct_calculation_wrong":
        grade_band = "formula_half_credit"
    elif quality_ratio >= 0.70 and strong_ratio >= 0.40 and not reject_hits and contradiction_count == 0:
        grade_band = "correct"
    elif contradiction_count >= 2 or (contradiction_count >= 1 and strong_ratio < 0.35):
        grade_band = "incorrect"
    elif quality_ratio >= 0.30 or (concept_coverage >= 0.30 and structure_score >= 0.25):
        grade_band = "partial"
    else:
        grade_band = "incorrect"

    if reject_hits and grade_band == "correct":
        grade_band = "partial"
    if reject_hits and contradiction_count and grade_band != "formula_half_credit":
        grade_band = "incorrect"

    score_ratio = quality_ratio
    if grade_band == "correct":
        score_ratio = max(score_ratio, min(1.0, 0.78 + 0.14 * concept_coverage + 0.08 * strong_ratio))
    elif grade_band == "partial":
        score_ratio = min(0.82, max(score_ratio, 0.35 + 0.38 * concept_coverage + 0.12 * structure_score))
    elif grade_band == "incorrect":
        score_ratio = min(score_ratio, 0.50)
    elif grade_band == "formula_half_credit":
        score_ratio = min(0.70, max(score_ratio, 0.50))
    if contradiction_count >= 2:
        score_ratio = min(score_ratio, 0.38)
    elif contradiction_count == 1:
        score_ratio = min(score_ratio, 0.58)

    score_ratio = float(max(0.0, min(1.0, score_ratio)))
    score = round(reference_question["max_marks"] * score_ratio, 1)

    matched_concepts = [entry["concept"] for entry in rubric_concepts if entry["status"] == "matched"]
    missed_concepts = [entry["concept"] for entry in rubric_concepts if entry["status"] != "matched"]
    matched_concept_ids = [entry["id"] for entry in rubric_concepts if entry["status"] == "matched"]
    missed_concept_ids = [entry["id"] for entry in rubric_concepts if entry["status"] != "matched"]

    metric_agreement_bonus = 0.15 if abs(concept_coverage - keyword_coverage) < 0.18 else 0.0
    confidence = 0.45 + 0.32 * strong_ratio + metric_agreement_bonus + 0.12 * length_factor
    if abs(concept_coverage - global_similarity_scaled) > 0.22:
        confidence -= 0.18
    if reject_hits:
        confidence -= 0.12
    if contradiction_count:
        confidence -= min(0.4, 0.14 * contradiction_count)
    if edge_case_type:
        confidence -= 0.06
    confidence = float(max(0.0, min(0.99, confidence)))

    feedback_summary = (
        f"Matched {len(matched_concepts)} rubric points and missed {len(missed_concepts)}. "
        f"Grounded alignment {round(display_similarity * 100)}%."
    )
    if reject_hits:
        feedback_summary += f" Possible misconception detected: {reject_hits[0]}."
    if contradiction_hits:
        feedback_summary += " One or more rubric concepts were contradicted by the student's wording."
    if edge_case_type == "formula_correct_calculation_wrong":
        feedback_summary += " Formula setup looks right but the numeric result appears incorrect."

    return {
        "score": score,
        "similarity": round(display_similarity, 4),
        "raw_similarity": round(global_similarity, 4),
        "concept_coverage": round(concept_coverage, 4),
        "keyword_coverage": round(keyword_coverage, 4),
        "structure_score": round(structure_score, 4),
        "formula_score": round(formula_score, 4),
        "numeric_score": round(numeric_score, 4),
        "strong_concept_ratio": round(strong_ratio, 4),
        "matched_keywords": matched_keywords,
        "matched_keyword_highlights": keyword_highlights,
        "missing_keywords": missing_keywords,
        "rubric_concepts": rubric_concepts,
        "matched_concepts": matched_concepts,
        "matched_concept_ids": matched_concept_ids,
        "missed_concepts": missed_concepts,
        "missed_concept_ids": missed_concept_ids,
        "grade_band": grade_band,
        "edge_case": edge_case_type,
        "edge_case_confidence": round(edge_case_confidence, 4),
        "score_ratio": round(score_ratio, 4),
        "semantic_signal": round(global_similarity_scaled, 4),
        "grading_confidence": round(confidence, 4),
        "feedback_summary": feedback_summary,
        "reject_hits": reject_hits,
        "contradiction_hits": contradiction_hits,
        "contradiction_count": contradiction_count,
        "grading_method": "deterministic",
        "answer_embedding_vector": student_embedding.tolist(),
    }


def merge_llm_review(reference_question: dict, deterministic_grade: dict, llm_review: dict | None) -> dict:
    if not llm_review:
        return deterministic_grade

    merged = dict(deterministic_grade)
    llm_ratio = max(0.0, min(1.0, float(llm_review.get("score_ratio", merged.get("score_ratio", 0.0)))))
    llm_confidence = max(0.0, min(1.0, float(llm_review.get("confidence", 0.0))))
    base_ratio = float(merged.get("score_ratio", 0.0))
    base_confidence = float(merged.get("grading_confidence", 0.0))

    agreement = llm_review.get("verdict") == merged.get("grade_band")
    llm_weight = 0.25 + 0.45 * llm_confidence
    if not agreement and llm_confidence >= 0.78:
        llm_weight = max(llm_weight, 0.62)

    final_ratio = (1.0 - llm_weight) * base_ratio + llm_weight * llm_ratio
    final_ratio = max(0.0, min(1.0, final_ratio))
    final_band = str(llm_review.get("verdict") or merged.get("grade_band") or "partial")
    if llm_confidence < 0.55:
        final_band = merged.get("grade_band", final_band)
    if llm_review.get("formula_correct_calculation_wrong"):
        final_band = "formula_half_credit"
        final_ratio = min(0.65, max(final_ratio, 0.45))
        merged["edge_case"] = "formula_correct_calculation_wrong"
        merged["edge_case_confidence"] = max(float(merged.get("edge_case_confidence", 0.0)), llm_confidence)
    if llm_review.get("contradiction_detected"):
        final_ratio = min(final_ratio, 0.42)
        final_band = "incorrect" if final_band != "formula_half_credit" else final_band

    merged["score_ratio"] = round(final_ratio, 4)
    merged["score"] = round(reference_question["max_marks"] * final_ratio, 1)
    merged["grade_band"] = final_band
    merged["grading_confidence"] = round(max(0.0, min(0.99, 0.55 * base_confidence + 0.45 * llm_confidence + (0.06 if agreement else -0.04))), 4)
    merged["grading_method"] = "deterministic_plus_llm"

    concept_lookup = {
        concept.get("id"): concept.get("description") or concept.get("concept")
        for concept in (reference_question.get("rubric_items") or [])
        if concept.get("id")
    }
    if llm_review.get("matched_concepts"):
        merged["matched_concept_ids"] = llm_review["matched_concepts"]
        merged["matched_concepts"] = [
            concept_lookup.get(concept_id, concept_id) for concept_id in llm_review["matched_concepts"]
        ]
    if llm_review.get("missed_concepts"):
        merged["missed_concept_ids"] = llm_review["missed_concepts"]
        merged["missed_concepts"] = [
            concept_lookup.get(concept_id, concept_id) for concept_id in llm_review["missed_concepts"]
        ]
    if llm_review.get("feedback"):
        merged["feedback_summary"] = llm_review["feedback"]

    return merged
