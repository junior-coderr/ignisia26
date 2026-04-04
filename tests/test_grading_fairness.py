import unittest
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").resolve()))

from src.pdf_processor import process_reference_pdf, process_student_pdf
from src.similarity_engine import grade_answer


class GradingFairnessTests(unittest.TestCase):
    def test_text_based_pdfs_extract_without_gemini(self):
        reference = process_reference_pdf(str(ROOT / "teachers.pdf"))
        student = process_student_pdf(str(ROOT / "datest-1.pdf"))
        wrong = process_student_pdf(str(ROOT / "wrong_answer_sheet.pdf"))

        self.assertEqual(len(reference.get("questions", [])), 4)
        self.assertEqual(len(student.get("answers", [])), 4)
        self.assertEqual(len(wrong.get("answers", [])), 4)
        self.assertEqual(reference["questions"][0]["q_number"], "Q1")
        self.assertEqual(student["answers"][0]["q_number"], "Q1")

    def test_exact_match_answer_gets_full_credit(self):
        reference_question = {
            "q_number": "Q1",
            "q_text": "Define data analysis.",
            "text": (
                "Data analysis is the process of inspecting, cleaning, transforming, and modeling "
                "data to extract useful insights and support decision-making."
            ),
            "max_marks": 10.0,
            "answer_text": (
                "Data analysis is the process of inspecting, cleaning, transforming, and modeling "
                "data to extract useful insights and support decision-making."
            ),
            "answer_embedding": np.asarray([1.0, 0.0], dtype=float),
            "rubric_segments": [
                "Defines data analysis as inspecting, cleaning, transforming, and modeling data.",
                "States that the goal is to extract useful insights and support decision-making.",
            ],
            "rubric_concept_ids": ["C1", "C2"],
            "rubric_weights": [0.5, 0.5],
            "rubric_keywords": ["analysis", "insights", "decision"],
            "formula_expected": None,
            "final_numeric_answer": None,
        }
        student_answer = {
            "q_number": "Q1",
            "text": (
                "Data analysis is the process of inspecting, cleaning, transforming, and modeling "
                "data to extract useful insights and support decision-making."
            ),
            "diagram_description": None,
        }

        grade = grade_answer(student_answer, reference_question, np.asarray([1.0, 0.0], dtype=float))

        self.assertEqual(grade["score"], 10.0)
        self.assertEqual(grade["score_ratio"], 1.0)
        self.assertEqual(grade["grade_band"], "correct")
        self.assertEqual(grade["grading_method"], "exact_match")
        self.assertEqual(grade["missed_concepts"], [])


if __name__ == "__main__":
    unittest.main()
