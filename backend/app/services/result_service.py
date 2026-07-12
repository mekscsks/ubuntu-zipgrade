"""
Result Service
Handles scan result operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import ScanResultResponse, ScanResultCreate, QuestionResult, ScanStatus


class ResultService(BaseService[ScanResultResponse, ScanResultCreate, ScanResultCreate]):
    """Service for scan result operations"""

    def __init__(self):
        super().__init__(Collections.RESULTS, ScanResultResponse)

    async def create_result(self, result_data: ScanResultCreate) -> ScanResultResponse:
        """Create a new scan result"""
        data = result_data.model_dump()
        data['reviewed_by_teacher'] = False
        data['review_notes'] = None
        return await self.create(data)

    async def get_results_by_exam(self, exam_id: str, limit: Optional[int] = None) -> List[ScanResultResponse]:
        """Get all results for an exam"""
        filters = [("exam_id", "==", exam_id)]
        return await self.get_all(
            filters=filters,
            order_by="created_at",
            order_direction="DESCENDING",
            limit=limit
        )

    async def get_results_by_student(self, student_id: str, limit: Optional[int] = None) -> List[ScanResultResponse]:
        """Get all results for a student"""
        filters = [("student_id", "==", student_id)]
        return await self.get_all(
            filters=filters,
            order_by="created_at",
            order_direction="DESCENDING",
            limit=limit
        )

    async def get_results_by_teacher(
        self,
        teacher_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ScanStatus] = None,
        exam_id: Optional[str] = None,
        class_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> tuple[List[ScanResultResponse], int]:
        """Get results for a teacher with filters"""
        filters = [("teacher_id", "==", teacher_id)]
        if status:
            filters.append(("status", "==", status.value))
        if exam_id:
            filters.append(("exam_id", "==", exam_id))
        if class_id:
            filters.append(("class_id", "==", class_id))
        if date_from:
            filters.append(("created_at", ">=", date_from))
        if date_to:
            filters.append(("created_at", "<=", date_to))

        results = await self.get_all(
            filters=filters,
            order_by="created_at",
            order_direction="DESCENDING",
            limit=page_size,
            offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return results, total

    async def get_results_pending_review(self, teacher_id: str) -> List[ScanResultResponse]:
        """Get results pending manual review"""
        filters = [
            ("teacher_id", "==", teacher_id),
            ("status", "==", ScanStatus.MANUAL_REVIEW.value)
        ]
        return await self.get_all(filters=filters, order_by="created_at", order_direction="ASCENDING")

    async def update_result_review(
        self,
        result_id: str,
        question_results: List[QuestionResult],
        review_notes: Optional[str] = None
    ) -> Optional[ScanResultResponse]:
        """Update result after manual review"""
        # Recalculate scores
        correct = sum(1 for q in question_results if q.is_correct)
        wrong = sum(1 for q in question_results if not q.is_correct and not q.is_blank)
        blank = sum(1 for q in question_results if q.is_blank)
        total = len(question_results)
        percentage = round((correct / total) * 100, 2) if total > 0 else 0

        from app.services.exam_service import exam_service
        exam = await exam_service.get_by_id(question_results[0].question_number if question_results else "")
        # Actually we need exam to get passing_score
        # Let's just get from result
        result = await self.get_by_id(result_id)
        if not result:
            return None

        passed = percentage >= result.passing_score if hasattr(result, 'passing_score') else percentage >= 60

        update_data = {
            "question_results": [q.model_dump() for q in question_results],
            "correct_count": correct,
            "wrong_count": wrong,
            "blank_count": blank,
            "percentage": percentage,
            "passed": passed,
            "reviewed_by_teacher": True,
            "review_notes": review_notes,
            "status": ScanStatus.COMPLETED.value,
        }
        return await self.update(result_id, update_data)

    async def get_student_exam_result(self, student_id: str, exam_id: str) -> Optional[ScanResultResponse]:
        """Get a specific student's result for an exam"""
        filters = [
            ("student_id", "==", student_id),
            ("exam_id", "==", exam_id)
        ]
        results = await self.get_all(filters=filters, limit=1)
        return results[0] if results else None

    async def get_exam_statistics(self, exam_id: str) -> Dict[str, Any]:
        """Get statistics for an exam"""
        results = await self.get_results_by_exam(exam_id)
        if not results:
            return {
                "total": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
                "passing_rate": 0,
                "score_distribution": {},
                "question_analysis": []
            }

        scores = [r.percentage for r in results]
        total_questions = results[0].total_questions if results else 0

        # Score distribution
        distribution = {
            "0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0
        }
        for score in scores:
            if score <= 20:
                distribution["0-20"] += 1
            elif score <= 40:
                distribution["21-40"] += 1
            elif score <= 60:
                distribution["41-60"] += 1
            elif score <= 80:
                distribution["61-80"] += 1
            else:
                distribution["81-100"] += 1

        # Question analysis
        question_analysis = []
        for q_num in range(1, total_questions + 1):
            correct = 0
            wrong = 0
            blank = 0
            multiple = 0
            options = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}

            for r in results:
                for qr in r.question_results:
                    if qr.question_number == q_num:
                        if qr.is_correct:
                            correct += 1
                        elif qr.is_blank:
                            blank += 1
                        elif qr.has_multiple_marks:
                            multiple += 1
                            wrong += 1
                        else:
                            wrong += 1
                        if qr.student_answer:
                            options[qr.student_answer] = options.get(qr.student_answer, 0) + 1

            total = len(results)
            difficulty = correct / total if total > 0 else 0

            question_analysis.append({
                "question_number": q_num,
                "correct_count": correct,
                "wrong_count": wrong,
                "blank_count": blank,
                "multiple_marks_count": multiple,
                "difficulty_index": round(difficulty, 3),
                "option_distribution": options
            })

        return {
            "total": len(results),
            "average_score": round(sum(scores) / len(scores), 2),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "passing_rate": round((sum(1 for s in scores if s >= 60) / len(scores)) * 100, 2),
            "score_distribution": distribution,
            "question_analysis": question_analysis
        }

    async def search(self, query: str, **kwargs) -> List[ScanResultResponse]:
        """Search results"""
        all_results = await self.get_all()
        q = query.lower()
        return [r for r in all_results if q in (r.student_name or "").lower()]

    async def delete_results_by_exam(self, exam_id: str) -> int:
        """Delete all results for an exam"""
        results = await self.get_results_by_exam(exam_id)
        doc_ids = [r.id for r in results]
        if doc_ids:
            return await self.batch_delete(doc_ids)
        return 0


result_service = ResultService()