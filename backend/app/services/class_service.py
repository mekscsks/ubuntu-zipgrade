"""
Class Service
Handles class-related operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import ClassResponse, ClassCreate, ClassUpdate


class ClassService(BaseService[ClassResponse, ClassCreate, ClassUpdate]):
    """Service for class operations"""

    def __init__(self):
        super().__init__(Collections.CLASSES, ClassResponse)

    async def create_class(self, class_data: ClassCreate) -> ClassResponse:
        """Create a new class"""
        data = class_data.model_dump()
        data['is_active'] = True
        data['student_count'] = 0
        return await self.create(data)

    async def get_classes_by_teacher(
        self,
        teacher_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        subject_id: Optional[str] = None
    ) -> tuple[List[ClassResponse], int]:
        """Get classes for a teacher"""
        filters = [("teacher_id", "==", teacher_id), ("is_active", "==", True)]
        if subject_id:
            filters.append(("subject_id", "==", subject_id))

        if search:
            all_classes = await self.get_all(filters=filters, order_by="name")
            filtered = [
                c for c in all_classes
                if search.lower() in c.name.lower()
                or search.lower() in c.section.lower()
                or search.lower() in c.grade_level.lower()
            ]
            total = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total

        classes = await self.get_all(
            filters=filters,
            order_by="name",
            order_direction="ASCENDING",
            limit=page_size,
            offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return classes, total

    async def get_class_with_students(self, class_id: str, teacher_id: str) -> Optional[ClassResponse]:
        """Get class with student count"""
        class_obj = await self.get_by_id(class_id)
        if not class_obj or class_obj.teacher_id != teacher_id:
            return None

        from app.services.student_service import student_service
        students, _ = await student_service.get_students_by_class(class_id)
        class_obj.student_count = len(students)
        return class_obj

    async def increment_student_count(self, class_id: str) -> bool:
        """Increment student count for class"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(class_id).update({"student_count": Increment(1)})
            return True
        except Exception:
            return False

    async def update_student_count(self, class_id: str, delta: int) -> bool:
        """Update student count"""
        from google.cloud.firestore import Increment
        try:
            self.collection.document(class_id).update({"student_count": Increment(delta)})
            return True
        except Exception:
            return False

    async def recalculate_student_count(self, class_id: str) -> int:
        """Recalculate and update student count"""
        from app.services.student_service import student_service
        students, _ = await student_service.get_students_by_class(class_id)
        count = len(students)
        await self.update(class_id, ClassUpdate(student_count=count))
        return count

    async def get_classes_by_subject(self, subject_id: str, teacher_id: str) -> List[ClassResponse]:
        """Get all classes for a subject"""
        return await self.get_all(filters=[
            ("subject_id", "==", subject_id),
            ("teacher_id", "==", teacher_id),
            ("is_active", "==", True)
        ], order_by="name")

    async def search(self, query: str, **kwargs) -> List[ClassResponse]:
        """Search classes"""
        return await self.search_classes(query, kwargs.get('teacher_id', ''), **kwargs)

    async def search_classes(self, query: str, teacher_id: str, **kwargs) -> List[ClassResponse]:
        """Search classes"""
        filters = [("teacher_id", "==", teacher_id), ("is_active", "==", True)]
        all_classes = await self.get_all(filters=filters, order_by="name")
        query_lower = query.lower()
        return [
            c for c in all_classes
            if query_lower in c.name.lower()
            or query_lower in c.section.lower()
            or query_lower in c.grade_level.lower()
        ]


class_service = ClassService()