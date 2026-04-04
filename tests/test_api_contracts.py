import unittest

from fastapi.testclient import TestClient

from src.main import _empty_metrics, app, exams


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        exams.clear()

    def tearDown(self):
        exams.clear()

    def test_summary_is_available_during_queued_state(self):
        exam_id = "exam_queued"
        exams[exam_id] = {
            "exam_id": exam_id,
            "status": "queued",
            "progress": 0.0,
            "title": "Reference Answer Key",
            "exam_code": "",
            "reference": {},
            "questions": [],
            "students": [],
            "error": None,
            "metrics": _empty_metrics(),
        }

        response = self.client.get(f"/api/exam/{exam_id}/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "queued")
        self.assertFalse(payload["reference_ready"])
        self.assertEqual(payload["question_count"], 0)

    def test_results_are_available_before_student_processing_finishes(self):
        exam_id = "exam_reference_ready"
        exams[exam_id] = {
            "exam_id": exam_id,
            "status": "reference_ready",
            "progress": 1.0,
            "title": "Sample Exam",
            "exam_code": "EX-42",
            "reference": {
                "questions": {
                    "Q1": {
                        "q_number": "Q1",
                        "q_text": "Explain gravity",
                        "max_marks": 5.0,
                        "text": "Gravity attracts masses.",
                    }
                }
            },
            "questions": ["Q1"],
            "students": [],
            "error": None,
            "metrics": _empty_metrics(),
        }

        response = self.client.get(f"/api/exam/{exam_id}/results")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "reference_ready")
        self.assertTrue(payload["reference_ready"])
        self.assertEqual(payload["questions"][0]["q_number"], "Q1")

    def test_clusters_endpoint_returns_empty_payload_while_exam_is_not_ready(self):
        exam_id = "exam_processing"
        exams[exam_id] = {
            "exam_id": exam_id,
            "status": "processing_reference",
            "progress": 0.5,
            "title": "Sample Exam",
            "exam_code": "",
            "reference": {},
            "questions": [],
            "students": [],
            "error": None,
            "metrics": _empty_metrics(),
        }

        response = self.client.get(f"/api/exam/{exam_id}/clusters")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "processing_reference")
        self.assertEqual(payload["clusters"], {})

    def test_cluster_payload_includes_compatibility_label(self):
        exam_id = "exam_clusters"
        shared_score = {
            "attempted": True,
            "score": 4.5,
            "score_ratio": 0.9,
            "similarity": 0.88,
            "concept_coverage": 0.9,
            "keyword_coverage": 0.85,
            "structure_score": 0.9,
            "formula_score": 0.0,
            "numeric_score": 0.0,
            "grading_confidence": 0.93,
            "grade_band": "correct",
            "edge_case": None,
            "matched_concepts": ["Defines gravity correctly"],
            "missed_concepts": [],
            "matched_keywords": ["gravity"],
            "matched_keyword_highlights": [],
            "reject_hits": [],
            "answer_embedding_vector": [1.0, 0.0, 0.0],
            "student_answer_text": "Gravity attracts masses toward each other.",
        }
        exams[exam_id] = {
            "exam_id": exam_id,
            "status": "ready",
            "progress": 1.0,
            "title": "Physics",
            "exam_code": "PHY-1",
            "reference": {
                "questions": {
                    "Q1": {
                        "q_number": "Q1",
                        "q_text": "Explain gravity",
                        "max_marks": 5.0,
                        "text": "Gravity attracts masses.",
                        "rubric_segments": ["Defines gravity correctly"],
                    }
                }
            },
            "questions": ["Q1"],
            "students": [
                {
                    "roll_number": "STU001",
                    "name": "Asha",
                    "scores": {"Q1": dict(shared_score)},
                },
                {
                    "roll_number": "STU002",
                    "name": "Rahul",
                    "scores": {"Q1": dict(shared_score)},
                },
            ],
            "error": None,
            "metrics": _empty_metrics(),
        }

        response = self.client.get(f"/api/exam/{exam_id}/clusters")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("Q1", payload["clusters"])
        self.assertGreaterEqual(len(payload["clusters"]["Q1"]), 1)
        cluster = payload["clusters"]["Q1"][0]
        self.assertEqual(cluster["label"], cluster["cluster_name"])


if __name__ == "__main__":
    unittest.main()
