"""
Students API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from typing import Optional, List

from app.schemas import (
    StudentResponse, StudentCreate, StudentUpdate, StudentImportRow, SuccessResponse
)
from app.services.student_service import student_service
from app.services.class_service import class_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()


@router.get("", response_model=List[StudentResponse])
async def list_students(
    class_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """List students for current teacher"""
    if class_id:
        # Verify class belongs to teacher
        class_obj = await class_service.get_by_id(class_id)
        if not class_obj or class_obj.teacher_id != current_user.uid:
            raise HTTPException(status_code=404, detail="Class not found")
        students, total = await student_service.get_students_by_class(class_id, page, page_size, search)
    else:
        students, total = await student_service.get_students_by_teacher(
            current_user.uid, page, page_size, search
        )
    return students


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new student"""
    student_data.teacher_id = current_user.uid
    return await student_service.create_student(student_data)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get student by ID"""
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    update_data: StudentUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update student"""
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")
    return await student_service.update_student(student_id, update_data)


@router.delete("/{student_id}", response_model=SuccessResponse)
async def delete_student(
    student_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete (deactivate) student"""
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")
    await student_service.update(student_id, StudentUpdate(is_active=False))
    # Decrement class count
    await class_service.update_student_count(student.class_id, -1)
    return SuccessResponse(message="Student deleted")


@router.post("/import", response_model=dict)
async def import_students(
    class_id: str,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Import students from Excel file"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    content = await file.read()
    result = await student_service.import_students_from_excel(content, class_id, current_user.uid)
    return result


@router.get("/export/excel")
async def export_students(
    class_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export students to Excel"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    excel_data = await student_service.export_students_to_excel(class_id, current_user.uid)

    from fastapi.responses import Response
    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=students_{class_id}.xlsx"}
    )


@router.get("/search", response_model=List[StudentResponse])
async def search_students(
    q: str,
    class_id: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Search students by name or student number"""
    return await student_service.search_students(q, class_id, current_user.uid)