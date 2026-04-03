"""
Embedding and similarity helpers for reference-answer grading.
"""
import os
import re
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

EMBED_MODEL = os.getenv("EMBED_MODEL", "paraphrase-multilingual-mpnet-base-v2")

_embedder = None


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
