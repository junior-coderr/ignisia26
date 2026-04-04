import unittest

from src.clustering_engine import run_clustering_for_question


def _student(
    roll_number: str,
    *,
    score: float = 2.0,
    score_ratio: float = 0.4,
    similarity: float = 0.5,
    grade_band: str = "partial",
    matched_concepts: list[str] | None = None,
    missed_concepts: list[str] | None = None,
    reject_hits: list[str] | None = None,
    edge_case: str | None = None,
):
    return {
        "roll_number": roll_number,
        "name": f"Student {roll_number}",
        "scores": {
            "Q1": {
                "attempted": True,
                "score": score,
                "score_ratio": score_ratio,
                "similarity": similarity,
                "concept_coverage": score_ratio * 0.9,
                "keyword_coverage": score_ratio * 0.85,
                "structure_score": score_ratio * 0.8,
                "formula_score": 0.0,
                "numeric_score": 0.0,
                "grading_confidence": 0.8,
                "grade_band": grade_band,
                "edge_case": edge_case,
                "matched_concepts": list(matched_concepts or []),
                "missed_concepts": list(missed_concepts or []),
                "matched_keywords": [],
                "matched_keyword_highlights": [],
                "reject_hits": list(reject_hits or []),
                "answer_embedding_vector": [1.0, 0.0, 0.0],
                "student_answer_text": "Sample answer",
            }
        },
    }


class ScoreBandClusteringTests(unittest.TestCase):

    def test_students_grouped_by_score_bands(self):
        """Students should be grouped into performance tiers by their score_ratio."""
        students = [
            _student("STU001", score=4.8, score_ratio=0.96, grade_band="correct",
                     matched_concepts=["Water cycle"]),
            _student("STU002", score=4.0, score_ratio=0.80, grade_band="correct",
                     matched_concepts=["Water cycle"], missed_concepts=["Condensation"]),
            _student("STU003", score=2.5, score_ratio=0.50, grade_band="partial",
                     matched_concepts=["Evaporation"], missed_concepts=["Condensation", "Precipitation"]),
            _student("STU004", score=1.0, score_ratio=0.20, grade_band="incorrect",
                     missed_concepts=["Water cycle", "Evaporation", "Condensation"]),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)

        # Should have bands for excellent (STU001), good (STU002), average (STU003), poor (STU004)
        kinds = [c["band_kind"] for c in clusters]
        self.assertIn("excellent", kinds)
        self.assertIn("good", kinds)
        self.assertIn("average", kinds)
        self.assertIn("poor", kinds)

        # Verify correct student placement
        for cluster in clusters:
            if cluster["band_kind"] == "excellent":
                rolls = [s["roll_number"] for s in cluster["students"]]
                self.assertIn("STU001", rolls)
            elif cluster["band_kind"] == "poor":
                rolls = [s["roll_number"] for s in cluster["students"]]
                self.assertIn("STU004", rolls)

    def test_insights_are_generated(self):
        """Each band should contain rich insights."""
        students = [
            _student("STU001", score=1.0, score_ratio=0.20, grade_band="incorrect",
                     missed_concepts=["Concept A", "Concept B"],
                     reject_hits=["confuses X with Y"]),
            _student("STU002", score=1.5, score_ratio=0.30, grade_band="incorrect",
                     missed_concepts=["Concept A", "Concept C"],
                     reject_hits=["confuses X with Y"]),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)

        self.assertEqual(len(clusters), 1)  # both in "poor" band
        cluster = clusters[0]

        # Check insights exist
        self.assertIn("insights", cluster)
        insights = cluster["insights"]
        self.assertIn("top_missed_concepts", insights)
        self.assertIn("misconceptions", insights)
        self.assertGreater(len(insights["top_missed_concepts"]), 0)
        self.assertGreater(len(insights["misconceptions"]), 0)

        # "Concept A" should be the most missed (appears in both students)
        top_missed_names = [c["concept"] for c in insights["top_missed_concepts"]]
        self.assertIn("Concept A", top_missed_names)

    def test_teaching_recommendations_present(self):
        """Each band should have a teaching recommendation."""
        students = [
            _student("STU001", score=4.5, score_ratio=0.90, grade_band="correct"),
            _student("STU002", score=1.0, score_ratio=0.20, grade_band="incorrect",
                     missed_concepts=["Core concept"]),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)

        for cluster in clusters:
            self.assertIn("teaching_recommendation", cluster)
            self.assertTrue(len(cluster["teaching_recommendation"]) > 0)

    def test_empty_students_returns_empty(self):
        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, [])
        self.assertEqual(clusters, [])

    def test_unattempted_excluded(self):
        students = [
            {"roll_number": "STU001", "name": "S1", "scores": {"Q1": {"attempted": False}}},
        ]
        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)
        self.assertEqual(clusters, [])

    def test_sorted_by_band_priority(self):
        """Clusters should be sorted: excellent → good → average → poor."""
        students = [
            _student("STU001", score=1.0, score_ratio=0.20),
            _student("STU002", score=4.8, score_ratio=0.96),
            _student("STU003", score=3.5, score_ratio=0.70),
            _student("STU004", score=2.5, score_ratio=0.50),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)
        kinds = [c["band_kind"] for c in clusters]

        priority = {"excellent": 0, "good": 1, "average": 2, "poor": 3}
        for i in range(len(kinds) - 1):
            self.assertLessEqual(priority[kinds[i]], priority[kinds[i + 1]])

    def test_score_range_metadata(self):
        """Each cluster should have score_range metadata."""
        students = [
            _student("STU001", score=4.8, score_ratio=0.95),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)
        self.assertEqual(len(clusters), 1)

        cluster = clusters[0]
        self.assertIn("score_range", cluster)
        self.assertIn("min_score", cluster["score_range"])
        self.assertIn("max_score", cluster["score_range"])
        self.assertEqual(cluster["band_kind"], "excellent")

    def test_backward_compatible_fields(self):
        """API response should still include backward-compatible fields."""
        students = [
            _student("STU001", score=3.0, score_ratio=0.60),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)

        cluster = clusters[0]
        # These fields existed in the old API
        self.assertIn("cluster_id", cluster)
        self.assertIn("cluster_name", cluster)
        self.assertIn("label", cluster)
        self.assertIn("cluster_kind", cluster)
        self.assertIn("is_outlier", cluster)
        self.assertIn("student_count", cluster)
        self.assertIn("avg_score", cluster)
        self.assertIn("avg_similarity", cluster)
        self.assertIn("common_pattern", cluster)
        self.assertIn("explanation", cluster)
        self.assertIn("insight", cluster)
        self.assertIn("students", cluster)

    def test_concept_frequency_in_insights(self):
        """Insights should include per-concept frequency analysis."""
        students = [
            _student("STU001", score=1.0, score_ratio=0.2,
                     matched_concepts=["A"], missed_concepts=["B", "C"]),
            _student("STU002", score=1.5, score_ratio=0.3,
                     matched_concepts=["A", "B"], missed_concepts=["C"]),
            _student("STU003", score=0.5, score_ratio=0.1,
                     missed_concepts=["A", "B", "C"]),
        ]

        clusters = run_clustering_for_question("Q1", {"max_marks": 5.0}, students)
        insights = clusters[0]["insights"]

        # concept_frequency should list all concepts with match/miss counts
        self.assertIn("concept_frequency", insights)
        concepts = {cf["concept"]: cf for cf in insights["concept_frequency"]}
        self.assertIn("C", concepts)
        # C is missed by all 3 students
        self.assertEqual(concepts["C"]["missed_count"], 3)


if __name__ == "__main__":
    unittest.main()
