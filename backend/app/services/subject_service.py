"""
Subject Service
Handles subject-related operations
"""
from typing import Optional, List, Dict, Any

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import SubjectResponse, SubjectCreate, SubjectUpdate


class SubjectService(BaseService[SubjectResponse, SubjectCreate, SubjectUpdate]):
    """Service for subject operations"""

    def __init__(self):
        super().__init__(Collections.SUBJECTS, SubjectResponse)

    async def create_subject(self, subject_data: SubjectCreate) -> SubjectResponse:
        """Create a new subject"""
        data = subject_data.model_dump()
        data['is_active'] = True
        data['total_exams'] = 0
        data['total_classes'] = 0
        return await self.create(data)

    async def get_subjects_by_teacher(
        self,
        teacher_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> tuple[List[SubjectResponse], int]:
        """Get subjects for a teacher"""
        filters = [("teacher_id", "==", teacher_id), ("is_active", "==", True)]

        if search:
            all_subjects = await self.get_all(filters=filters, order_by="name")
            filtered = [
                s for s in all_subjects
                if search.lower() in s.name.lower()
                or search.lower() in s.code.lower()
                or (s.description and search.lower() in s.description.lower())
            ]
            total = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total

        subjects = await self.get_all(
            filters=filters,
            order_by="name",
            order_direction="ASCENDING",
            limit=page_size,
            offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return subjects, total

    async def get_subject_with_stats(self, subject_id: str, teacher_id: str) -> Optional[SubjectResponse]:
        """Get subject with computed statistics"""
        subject = await self.get_by_id(subject_id)
        if not subject or subject.teacher_id != teacher_id:
            return None

        from app.firebase.init_firebase import get_firestore_client
        db = get_firestore_client()

        from google.cloud.firestore_v1.base_query import FieldFilter
        # Count exams
        exams_count = len(list(db.collection(Collections.EXAMS)
            .where(filter=FieldFilter("subject_id", "==", subject_id))
            .get()))

        # Count classes
        classes_count = len(list(db.collection(Collections.CLASSES)
            .where(filter=FieldFilter("subject_id", "==", subject_id))
            .get()))

        subject.total_exams = exams_count
        subject.total_classes = classes_count

        return subject

    async def increment_exam_count(self, subject_id: str) -> bool:
        """Increment exam count for subject"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(subject_id).update({"total_exams": Increment(1)})
            return True
        except Exception:
            return False

    async def increment_class_count(self, subject_id: str) -> bool:
        """Increment class count for subject"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(subject_id).update({"total_classes": Increment(1)})
            return True
        except Exception:
            return False

    async def decrement_exam_count(self, subject_id: str) -> bool:
        """Decrement exam count for subject"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(subject_id).update({"total_exams": Increment(-1)})
            return True
        except Exception:
            return False

    async def decrement_class_count(self, subject_id: str) -> bool:
        """Decrement class count for subject"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(subject_id).update({"total_classes": Increment(-1)})
            return True
        except Exception:
            return False

    async def search(self, query: str, teacher_id: str, **kwargs) -> List[SubjectResponse]:
        """Search subjects"""
        filters = [("teacher_id", "==", teacher_id), ("is_active", "==", True)]
        all_subjects = await self.get_all(filters=filters, order_by="name")
        query_lower = query.lower()
        return [
            s for s in all_subjects
            if query_lower in s.name.lower()
            or query_lower in s.code.lower()
        ]


subject_service = SubjectService()