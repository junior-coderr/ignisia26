"""
Phase 4: Grade storage & one-action application
- Apply a score + feedback to an entire cluster → propagates to all mapped students
"""
from typing import Optional


class GradingEngine:
    def __init__(self):
        # grades[exam_id][roll_number][q_number] = {score, feedback}
        self.grades: dict = {}
        # cluster_grades[exam_id][cluster_id] = {score, feedback}
        self.cluster_grades: dict = {}

    def apply_grade(
        self,
        exam_id: str,
        q_number: str,
        cluster_id: str,
        students: list,          # list of {roll_number, name, ...}
        score: float,
        feedback: str = "",
    ) -> int:
        """Apply grade to all students in a cluster. Returns count of students graded."""
        self.grades.setdefault(exam_id, {})
        self.cluster_grades.setdefault(exam_id, {})

        self.cluster_grades[exam_id][cluster_id] = {
            "score": score,
            "feedback": feedback,
            "graded": True,
        }

        count = 0
        for student in students:
            roll = student["roll_number"]
            self.grades[exam_id].setdefault(roll, {
                "name": student.get("name", ""),
                "roll_number": roll,
                "scores": {}
            })
            self.grades[exam_id][roll]["scores"][q_number] = {
                "score": score,
                "feedback": feedback,
                "cluster_id": cluster_id,
            }
            count += 1
        return count

    def get_student_grades(self, exam_id: str) -> list:
        return list(self.grades.get(exam_id, {}).values())

    def is_cluster_graded(self, exam_id: str, cluster_id: str) -> bool:
        return self.cluster_grades.get(exam_id, {}).get(cluster_id, {}).get("graded", False)

    def get_cluster_grade(self, exam_id: str, cluster_id: str) -> Optional[dict]:
        return self.cluster_grades.get(exam_id, {}).get(cluster_id)

    def grading_progress(self, exam_id: str, clusters_by_question: dict) -> dict:
        """Returns per-question progress and overall percentage."""
        progress = {}
        total_clusters = 0
        graded_clusters = 0
        for q, clusters in clusters_by_question.items():
            all_c = clusters.get("clusters", []) + clusters.get("edge_cases", [])
            q_total = len(all_c)
            q_graded = sum(1 for c in all_c if self.is_cluster_graded(exam_id, c["cluster_id"]))
            progress[q] = {"graded": q_graded, "total": q_total}
            total_clusters += q_total
            graded_clusters += q_graded
        overall = round(graded_clusters / total_clusters, 2) if total_clusters else 0.0
        return {"by_question": progress, "overall": overall,
                "graded_clusters": graded_clusters, "total_clusters": total_clusters}


# Singleton
grading_engine = GradingEngine()
