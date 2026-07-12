"""
Student Service
Handles student-related operations
"""
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import io
import logging

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections, get_firestore_client
from app.schemas import StudentResponse, StudentCreate, StudentUpdate, StudentImportRow

logger = logging.getLogger(__name__)


class StudentService(BaseService[StudentResponse, StudentCreate, StudentUpdate]):
    """Service for student operations"""

    def __init__(self):
        super().__init__(Collections.STUDENTS, StudentResponse)

    async def create_student(self, student_data: StudentCreate) -> StudentResponse:
        """Create a new student"""
        data = student_data.model_dump()
        data['is_active'] = True
        # Generate QR code will be done later
        return await self.create(data)

    async def get_students_by_teacher(
        self,
        teacher_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> tuple[List[StudentResponse], int]:
        """Get all students for a teacher"""
        filters = [("teacher_id", "==", teacher_id), ("is_active", "==", True)]
        if search:
            all_students = await self.get_all(filters=filters, order_by="last_name")
            search_lower = search.lower()
            filtered = [
                s for s in all_students
                if search_lower in f"{s.first_name} {s.last_name}".lower()
                or search_lower in s.student_number.lower()
            ]
            total = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total
        students = await self.get_all(
            filters=filters, order_by="last_name",
            limit=page_size, offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return students, total

    async def get_students_by_class(
        self,
        class_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        section: Optional[str] = None
    ) -> tuple[List[StudentResponse], int]:
        """Get students in a class"""
        filters = [("class_id", "==", class_id), ("is_active", "==", True)]
        if section:
            filters.append(("section", "==", section))

        if search:
            all_students = await self.get_all(filters=filters, order_by="last_name")
            search_lower = search.lower()
            filtered = [
                s for s in all_students
                if search_lower in f"{s.first_name} {s.last_name}".lower()
                or search_lower in s.student_number.lower()
                or (s.email and search_lower in s.email.lower())
            ]
            total = len(filtered)
            offset = (page - 1) * page_size
            return filtered[offset:offset + page_size], total

        students = await self.get_all(
            filters=filters,
            order_by="last_name",
            order_direction="ASCENDING",
            limit=page_size,
            offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return students, total

    async def get_student_by_number(self, student_number: str, class_id: str) -> Optional[StudentResponse]:
        """Get student by student number in a class"""
        docs = self.collection.where(filter=("student_number", "==", student_number)).where(
            filter=("class_id", "==", class_id)).where(filter=("is_active", "==", True)).limit(1).get()
        for doc in docs:
            return self._doc_to_model(doc)
        return None

    async def update_student(self, student_id: str, update_data: StudentUpdate) -> Optional[StudentResponse]:
        """Update student"""
        data = update_data.model_dump(exclude_unset=True)
        return await self.update(student_id, data)

    async def import_students_from_excel(
        self,
        file_content: bytes,
        class_id: str,
        teacher_id: str
    ) -> Dict[str, Any]:
        """Import students from Excel file"""
        try:
            df = pd.read_excel(io.BytesIO(file_content))

            # Validate required columns
            required_cols = ['student_number', 'first_name', 'last_name']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return {
                    "success": False,
                    "error": f"Missing required columns: {missing_cols}",
                    "imported": 0,
                    "errors": []
                }

            students_to_import = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    student_data = StudentImportRow(
                        student_number=str(row['student_number']).strip(),
                        first_name=str(row['first_name']).strip(),
                        last_name=str(row['last_name']).strip(),
                        section=str(row['section']).strip() if 'section' in row and pd.notna(row['section']) else None,
                        grade=str(row['grade']).strip() if 'grade' in row and pd.notna(row['grade']) else None,
                        email=str(row['email']).strip() if 'email' in row and pd.notna(row['email']) else None,
                        phone=str(row['phone']).strip() if 'phone' in row and pd.notna(row['phone']) else None,
                        parent_name=str(row['parent_name']).strip() if 'parent_name' in row and pd.notna(row['parent_name']) else None,
                        parent_phone=str(row['parent_phone']).strip() if 'parent_phone' in row and pd.notna(row['parent_phone']) else None,
                        parent_email=str(row['parent_email']).strip() if 'parent_email' in row and pd.notna(row['parent_email']) else None,
                    )

                    # Check for duplicate student number
                    existing = await self.get_student_by_number(student_data.student_number, class_id)
                    if existing:
                        errors.append(f"Row {idx + 2}: Student number {student_data.student_number} already exists")
                        continue

                    students_to_import.append({
                        "student_number": student_data.student_number,
                        "first_name": student_data.first_name,
                        "last_name": student_data.last_name,
                        "section": student_data.section,
                        "grade": student_data.grade,
                        "email": student_data.email,
                        "phone": student_data.phone,
                        "parent_name": student_data.parent_name,
                        "parent_phone": student_data.parent_phone,
                        "parent_email": student_data.parent_email,
                        "class_id": class_id,
                        "teacher_id": teacher_id,
                        "is_active": True,
                    })

                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")

            # Batch import
            if students_to_import:
                doc_ids = await self.batch_create(students_to_import)

                # Update class student count
                from app.services.class_service import class_service
                await class_service.increment_student_count(class_id)

                return {
                    "success": True,
                    "imported": len(doc_ids),
                    "errors": errors,
                    "student_ids": doc_ids
                }

            return {
                "success": True,
                "imported": 0,
                "errors": errors,
                "student_ids": []
            }

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported": 0,
                "errors": []
            }

    async def export_students_to_excel(
        self,
        class_id: str,
        teacher_id: str
    ) -> bytes:
        """Export students to Excel"""
        students, _ = await self.get_students_by_class(class_id, page=1, page_size=10000)

        # Verify teacher owns the class
        from app.services.class_service import class_service
        class_obj = await class_service.get_by_id(class_id)
        if not class_obj or class_obj.teacher_id != teacher_id:
            raise ValueError("Unauthorized")

        data = []
        for s in students:
            data.append({
                "Student Number": s.student_number,
                "First Name": s.first_name,
                "Last Name": s.last_name,
                "Section": s.section or "",
                "Grade": s.grade or "",
                "Email": s.email or "",
                "Phone": s.phone or "",
                "Parent Name": s.parent_name or "",
                "Parent Phone": s.parent_phone or "",
                "Parent Email": s.parent_email or "",
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
        return output.getvalue()

    async def search(self, query: str, **kwargs) -> List[StudentResponse]:
        """Search students"""
        return await self.search_students(query, **kwargs)

    async def search_students(
        self,
        query: str,
        class_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        **kwargs
    ) -> List[StudentResponse]:
        """Search students"""
        filters = [("is_active", "==", True)]
        if class_id:
            filters.append(("class_id", "==", class_id))
        if teacher_id:
            filters.append(("teacher_id", "==", teacher_id))

        all_students = await self.get_all(filters=filters, order_by="last_name")
        query_lower = query.lower()
        return [
            s for s in all_students
            if query_lower in f"{s.first_name} {s.last_name}".lower()
            or query_lower in s.student_number.lower()
            or (s.email and query_lower in s.email.lower())
        ]

    async def generate_qr_code_url(self, student_id: str) -> Optional[str]:
        """Generate QR code URL for student (placeholder - actual generation in scanner service)"""
        student = await self.get_by_id(student_id)
        if student:
            return student.qr_code_url
        return None


student_service = StudentService()