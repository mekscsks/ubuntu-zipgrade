"""
Exam Service
Handles exam-related operations
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import ExamResponse, ExamCreate, ExamUpdate, ExamStatus


class ExamService(BaseService[ExamResponse, ExamCreate, ExamUpdate]):
    """Service for exam operations"""

    def __init__(self):
        super().__init__(Collections.EXAMS, ExamResponse)

    async def create_exam(self, exam_data: ExamCreate) -> ExamResponse:
        """Create a new exam"""
        data = exam_data.model_dump()
        data['teacher_id'] = exam_data.teacher_id
        data['status'] = ExamStatus.DRAFT
        data['total_scans'] = 0
        data['average_score'] = None
        data['highest_score'] = None
        data['lowest_score'] = None
        data['passing_rate'] = None
        return await self.create(data)

    async def get_exams_by_teacher(
        self,
        teacher_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[ExamStatus] = None,
        subject_id: Optional[str] = None,
        class_id: Optional[str] = None
    ) -> tuple[List[ExamResponse], int]:
        """Get exams for a teacher"""
        filters = [("teacher_id", "==", teacher_id)]
        if status:
            filters.append(("status", "==", status.value))
        if subject_id:
            filters.append(("subject_id", "==", subject_id))
        if class_id:
            filters.append(("class_id", "==", class_id))

        if search:
            all_exams = await self.get_all(filters=filters, order_by="created_at", order_direction="DESCENDING")
            search_lower = search.lower()
            filtered = [
                e for e in all_exams
                if search_lower in e.title.lower()
                or (e.description and search_lower in e.description.lower())
            ]
            total = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total

        exams = await self.get_all(
            filters=filters,
            order_by="created_at",
            order_direction="DESCENDING",
            limit=page_size,
            offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return exams, total

    async def get_exam_with_stats(self, exam_id: str, teacher_id: str) -> Optional[ExamResponse]:
        """Get exam with computed statistics"""
        exam = await self.get_by_id(exam_id)
        if not exam or exam.teacher_id != teacher_id:
            return None

        from app.firebase.init_firebase import get_firestore_client
        from app.services.result_service import result_service

        # Get results for this exam
        results = await result_service.get_results_by_exam(exam_id)
        if results:
            scores = [r.percentage for r in results]
            exam.total_scans = len(results)
            exam.average_score = round(sum(scores) / len(scores), 2)
            exam.highest_score = max(scores)
            exam.lowest_score = min(scores)
            passed = sum(1 for s in scores if s >= exam.passing_score)
            exam.passing_rate = round((passed / len(scores)) * 100, 2)

        return exam

    async def publish_exam(self, exam_id: str, teacher_id: str) -> Optional[ExamResponse]:
        """Publish an exam"""
        exam = await self.get_by_id(exam_id)
        if not exam or exam.teacher_id != teacher_id:
            return None
        return await self.update(exam_id, ExamUpdate(status=ExamStatus.PUBLISHED))

    async def archive_exam(self, exam_id: str, teacher_id: str) -> Optional[ExamResponse]:
        """Archive an exam"""
        exam = await self.get_by_id(exam_id)
        if not exam or exam.teacher_id != teacher_id:
            return None
        return await self.update(exam_id, ExamUpdate(status=ExamStatus.ARCHIVED))

    async def duplicate_exam(self, exam_id: str, teacher_id: str, new_title: str) -> Optional[ExamResponse]:
        """Duplicate an exam"""
        exam = await self.get_by_id(exam_id)
        if not exam or exam.teacher_id != teacher_id:
            return None

        new_exam_data = ExamCreate(
            teacher_id=teacher_id,
            title=new_title,
            description=exam.description,
            instructions=exam.instructions,
            subject_id=exam.subject_id,
            class_id=exam.class_id,
            num_questions=exam.num_questions,
            passing_score=exam.passing_score,
            duration_minutes=exam.duration_minutes,
            answer_key=exam.answer_key,
            allow_multiple_answers=exam.allow_multiple_answers,
            shuffle_questions=exam.shuffle_questions,
            shuffle_options=exam.shuffle_options,
            show_results_immediately=exam.show_results_immediately,
            paper_size=exam.paper_size,
        )
        return await self.create_exam(new_exam_data)

    async def increment_scan_count(self, exam_id: str) -> bool:
        """Increment scan count for exam"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(exam_id).update({"total_scans": Increment(1)})
            return True
        except Exception:
            return False

    async def update_exam_stats(self, exam_id: str) -> Optional[ExamResponse]:
        """Recalculate and update exam statistics"""
        from app.services.result_service import result_service

        results = await result_service.get_results_by_exam(exam_id)
        if not results:
            return await self.update(exam_id, ExamUpdate(
                total_scans=0,
                average_score=None,
                highest_score=None,
                lowest_score=None,
                passing_rate=None
            ))

        scores = [r.percentage for r in results]
        exam = await self.get_by_id(exam_id)
        passing_score = exam.passing_score if exam else 60

        return await self.update(exam_id, ExamUpdate(
            total_scans=len(results),
            average_score=round(sum(scores) / len(scores), 2),
            highest_score=max(scores),
            lowest_score=min(scores),
            passing_rate=round((sum(1 for s in scores if s >= passing_score) / len(scores)) * 100, 2)
        ))

    async def search(self, query: str, **kwargs) -> List[ExamResponse]:
        """Search exams"""
        return await self.search_exams(query, kwargs.get('teacher_id', ''), **kwargs)

    async def search_exams(self, query: str, teacher_id: str, **kwargs) -> List[ExamResponse]:
        """Search exams"""
        filters = [("teacher_id", "==", teacher_id)]
        all_exams = await self.get_all(filters=filters, order_by="created_at", order_direction="DESCENDING")
        query_lower = query.lower()
        return [
            e for e in all_exams
            if query_lower in e.title.lower()
            or (e.description and query_lower in e.description.lower())
        ]


exam_service = ExamService()