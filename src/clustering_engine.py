"""
Phase 2 & 3: Embedding + Isolated Clustering Engine
- Semantic concatenation: [Text]: ... | [Diagram]: ...
- Multilingual embeddings via sentence-transformers
- HDBSCAN per question (noise = edge cases)
- Medoid selection for cluster representative
- Gemini labels each cluster
"""
import os
import json
import numpy as np
import hdbscan
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

from gemini_compat import DEFAULT_GEMINI_MODEL, gemini_enabled, generate_content, response_text

load_dotenv()
GEMINI_MODEL = DEFAULT_GEMINI_MODEL
EMBED_MODEL  = "paraphrase-multilingual-mpnet-base-v2"

_embedder = None

def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def make_combined_text(answer: dict) -> str:
    text = (answer.get("text") or "").strip()
    diag = (answer.get("diagram_description") or "").strip()
    if diag and diag.lower() not in ("none", "null", ""):
        return f"[Text]: {text} | [Diagram]: {diag}"
    return f"[Text]: {text}"


def _find_medoid(members: list, embeddings: np.ndarray) -> dict:
    centroid = embeddings.mean(axis=0, keepdims=True)
    sims = cosine_similarity(centroid, embeddings)[0]
    return members[int(np.argmax(sims))]


def label_cluster(sample_texts: list[str], rubric_keywords: list[str], q_text: str) -> dict:
    if not gemini_enabled():
        return {"label": f"Cluster ({len(sample_texts)} answers)", "type": "partial",
                "matched_keywords": [], "confidence": 0.5}

    samples = "\n---\n".join(t[:400] for t in sample_texts[:3])
    kw = ", ".join(rubric_keywords) if rubric_keywords else "not provided"
    prompt = f"""Grading assistant. Question: "{q_text}"
Sample answers from one cluster:
---
{samples}
---
Rubric keywords: {kw}

Return ONLY valid JSON:
{{
  "label": "Short descriptive label, e.g. 'Correct – full explanation with diagram'",
  "type": "correct" | "partial" | "incorrect",
  "matched_keywords": ["keyword1"],
  "confidence": 0.85
}}"""
    try:
        resp = generate_content(GEMINI_MODEL, prompt)
        text = response_text(resp).strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return {"label": f"Cluster ({len(sample_texts)} answers)", "type": "partial",
                "matched_keywords": [], "confidence": 0.5}


def cluster_question(
    q_number: str,
    student_answers: list,      # [{roll_number, name, answer: {text, diagram_*}}]
    rubric: dict,               # {q_text, max_marks, keywords}
    use_gemini_labels: bool = True
) -> dict:
    """
    Returns:
      {clusters: [{cluster_id, label, type, students, representative, ...}],
       edge_cases: [{...}]}
    """
    if not student_answers:
        return {"clusters": [], "edge_cases": []}

    keywords = rubric.get("keywords", [])
    q_text = rubric.get("q_text", q_number)
    max_marks = rubric.get("max_marks", 5)

    if len(student_answers) == 1:
        member = {**student_answers[0], "combined_text": make_combined_text(student_answers[0]["answer"])}
        matched_kw = [k for k in keywords if k.lower() in member["combined_text"].lower()]
        kw_pct = len(matched_kw) / len(keywords) if keywords else 0.0
        return {
            "clusters": [],
            "edge_cases": [{
                "cluster_id": f"{q_number}_edge_0",
                "label": "Edge Case – single submitted answer",
                "type": "edge_case",
                "student_count": 1,
                "students": [member],
                "representative": member,
                "matched_keywords": matched_kw,
                "keyword_match_pct": round(kw_pct, 2),
                "suggested_score": round(kw_pct * max_marks, 1),
                "graded": False,
                "score": None,
                "feedback": "",
            }],
        }

    embedder = get_embedder()
    combined = [make_combined_text(sa["answer"]) for sa in student_answers]
    embeddings = embedder.encode(combined, normalize_embeddings=True)

    min_size = max(2, len(student_answers) // 8)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom"
    )
    labels = clusterer.fit_predict(embeddings)

    raw_clusters: dict = {}
    edge_case_members = []

    for i, lbl in enumerate(labels):
        record = {**student_answers[i], "combined_text": combined[i]}
        if lbl == -1:
            edge_case_members.append(record)
        else:
            raw_clusters.setdefault(lbl, {"members": [], "embs": []})
            raw_clusters[lbl]["members"].append(record)
            raw_clusters[lbl]["embs"].append(embeddings[i])

    def build_cluster_obj(cluster_id: str, members: list, embs: np.ndarray, is_edge: bool = False):
        rep = _find_medoid(members, embs)
        sample_texts = [m["combined_text"] for m in members]
        matched_kw = [k for k in keywords if any(k.lower() in t.lower() for t in sample_texts)]
        kw_pct = len(matched_kw) / len(keywords) if keywords else 0.0
        suggested = round(kw_pct * max_marks, 1)

        label_data = {"label": "Edge Case – unique answer", "type": "edge_case",
                      "matched_keywords": matched_kw, "confidence": 0.5}
        if not is_edge and use_gemini_labels:
            label_data = label_cluster(sample_texts, keywords, q_text)
            label_data["matched_keywords"] = matched_kw

        return {
            "cluster_id": cluster_id,
            "label": label_data["label"],
            "type": "edge_case" if is_edge else label_data.get("type", "partial"),
            "student_count": len(members),
            "students": members,
            "representative": rep,
            "matched_keywords": matched_kw,
            "keyword_match_pct": round(kw_pct, 2),
            "suggested_score": suggested,
            "graded": False,
            "score": None,
            "feedback": "",
        }

    clusters = []
    for lbl, data in sorted(raw_clusters.items()):
        embs_arr = np.array(data["embs"])
        cid = f"{q_number}_cluster_{lbl}"
        clusters.append(build_cluster_obj(cid, data["members"], embs_arr))

    # Sort: correct → partial → incorrect
    order = {"correct": 0, "partial": 1, "incorrect": 2, "edge_case": 3}
    clusters.sort(key=lambda c: order.get(c["type"], 2))

    edge_cases = []
    for i, ec in enumerate(edge_case_members):
        emb = embeddings[list(combined).index(ec["combined_text"])].reshape(1, -1)
        cid = f"{q_number}_edge_{i}"
        edge_cases.append(build_cluster_obj(cid, [ec], emb, is_edge=True))

    return {"clusters": clusters, "edge_cases": edge_cases}
