"""
Teacher Service
Handles teacher-related operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import TeacherResponse, TeacherCreate, TeacherUpdate, TeacherSettings


class TeacherService(BaseService[TeacherResponse, TeacherCreate, TeacherUpdate]):
    """Service for teacher operations"""

    def __init__(self):
        super().__init__(Collections.TEACHERS, TeacherResponse)

    async def create_teacher(self, teacher_data: TeacherCreate, uid: str) -> TeacherResponse:
        """Create teacher profile from Firebase Auth user"""
        data = teacher_data.model_dump()
        data['uid'] = uid
        data['is_active'] = True
        data['last_login'] = datetime.utcnow()
        doc_ref = self.collection.document(uid)
        doc_ref.set({**data, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()})
        return self._doc_to_model(doc_ref.get())

    async def get_by_uid(self, uid: str) -> Optional[TeacherResponse]:
        """Get teacher by Firebase UID"""
        return await self.get_by_id(uid)

    async def get_by_email(self, email: str) -> Optional[TeacherResponse]:
        """Get teacher by email"""
        docs = self.collection.where(filter=("email", "==", email)).limit(1).get()
        for doc in docs:
            return self._doc_to_model(doc)
        return None

    async def update_teacher(self, uid: str, update_data: TeacherUpdate) -> Optional[TeacherResponse]:
        """Update teacher profile"""
        return await self.update(uid, update_data)

    async def update_last_login(self, uid: str):
        """Update teacher's last login timestamp"""
        self.collection.document(uid).update({'last_login': datetime.utcnow(), 'updated_at': datetime.utcnow()})

    async def get_settings(self, uid: str) -> TeacherSettings:
        """Get teacher settings"""
        teacher = await self.get_by_id(uid)
        if teacher:
            return TeacherSettings(
                school_name=teacher.school_name or "My School",
                school_logo_url=teacher.school_logo_url,
                theme=getattr(teacher, 'theme', 'system'),
                dark_mode=getattr(teacher, 'dark_mode', False),
                passing_percentage=getattr(teacher, 'passing_percentage', 60.0),
                paper_size=getattr(teacher, 'paper_size', 'A4'),
                bubble_size=getattr(teacher, 'bubble_size', 'medium'),
                scan_sensitivity=getattr(teacher, 'scan_sensitivity', 0.7),
            )
        return TeacherSettings()

    async def update_settings(self, uid: str, settings: TeacherSettings) -> Optional[TeacherResponse]:
        """Update teacher settings"""
        data = settings.model_dump()
        return await self.update(uid, data)

    async def search(self, query: str, **kwargs) -> list:
        """Search teachers by name or email"""
        all_teachers = await self.get_all()
        q = query.lower()
        return [t for t in all_teachers if q in (t.full_name or "").lower() or q in (t.email or "").lower()]

    async def deactivate_teacher(self, uid: str) -> bool:
        """Deactivate teacher account"""
        return await self.update(uid, {"is_active": False}) is not None

    async def get_dashboard_stats(self, uid: str) -> Dict[str, Any]:
        """Get dashboard statistics for teacher"""
        from app.firebase.init_firebase import get_firestore_client
        db = get_firestore_client()

        # Count students
        from google.cloud.firestore_v1.base_query import FieldFilter
        students_count = len(list(db.collection(Collections.STUDENTS).where(filter=FieldFilter("teacher_id", "==", uid)).get()))

        # Count classes
        classes_count = len(list(db.collection(Collections.CLASSES).where(filter=FieldFilter("teacher_id", "==", uid)).get()))

        # Count subjects
        subjects_count = len(list(db.collection(Collections.SUBJECTS).where(filter=FieldFilter("teacher_id", "==", uid)).get()))

        # Count exams
        exams_count = len(list(db.collection(Collections.EXAMS).where(filter=FieldFilter("teacher_id", "==", uid)).get()))

        # Get recent exams
        recent_exams_docs = db.collection(Collections.EXAMS).where(filter=FieldFilter("teacher_id", "==", uid)).order_by("created_at", direction="DESCENDING").limit(5).get()
        recent_exams = [TeacherResponse(**doc.to_dict(), id=doc.id) for doc in recent_exams_docs]

        # Get recent scans
        recent_scans_docs = db.collection(Collections.SCAN_HISTORY).where(filter=FieldFilter("teacher_id", "==", uid)).order_by("created_at", direction="DESCENDING").limit(10).get()
        recent_scans = [doc.to_dict() for doc in recent_scans_docs]

        # Calculate average score
        results_docs = db.collection(Collections.RESULTS).where(filter=FieldFilter("teacher_id", "==", uid)).get()
        scores = [doc.to_dict().get('percentage', 0) for doc in results_docs]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Scans today
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        scans_today = len(list(db.collection(Collections.SCAN_HISTORY)
            .where(filter=FieldFilter("teacher_id", "==", uid))
            .where(filter=FieldFilter("created_at", ">=", today_start))
            .get()))

        # Pending reviews
        pending_reviews = len(list(db.collection(Collections.RESULTS)
            .where(filter=FieldFilter("teacher_id", "==", uid))
            .where(filter=FieldFilter("status", "==", "manual_review"))
            .get()))

        return {
            "total_students": students_count,
            "total_classes": classes_count,
            "total_subjects": subjects_count,
            "total_exams": exams_count,
            "average_score": round(avg_score, 2),
            "total_scans_today": scans_today,
            "pending_reviews": pending_reviews,
            "recent_exams": recent_exams,
            "recent_scans": recent_scans,
        }


teacher_service = TeacherService()