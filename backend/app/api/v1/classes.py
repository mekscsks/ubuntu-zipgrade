"""
Classes API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List

from app.schemas import (
    ClassResponse, ClassCreate, ClassUpdate, SuccessResponse
)
from app.services.class_service import class_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()


@router.get("", response_model=List[ClassResponse])
async def list_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    subject_id: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """List classes for current teacher"""
    classes, total = await class_service.get_classes_by_teacher(
        current_user.uid, page, page_size, search, subject_id
    )
    return classes


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    class_data: ClassCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new class"""
    class_data.teacher_id = current_user.uid
    return await class_service.create_class(class_data)


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get class by ID with student count"""
    class_obj = await class_service.get_class_with_students(class_id, current_user.uid)
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_obj


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: str,
    update_data: ClassUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update class"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")
    return await class_service.update(class_id, update_data)


@router.delete("/{class_id}", response_model=SuccessResponse)
async def delete_class(
    class_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete (deactivate) class"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")
    await class_service.update(class_id, ClassUpdate(is_active=False))
    return SuccessResponse(message="Class deleted")


@router.get("/{class_id}/students")
async def get_class_students(
    class_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Get students in a class"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    from app.services.student_service import student_service
    students, total = await student_service.get_students_by_class(
        class_id, page, page_size, search
    )
    return {"students": students, "total": total}


@router.post("/{class_id}/students/import")
async def import_students(
    class_id: str,
    file: bytes,
    current_user: TokenData = Depends(get_current_user)
):
    """Import students from Excel file"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    from app.services.student_service import student_service
    result = await student_service.import_students_from_excel(file, class_id, current_user.uid)
    return result


@router.get("/{class_id}/students/export")
async def export_students(
    class_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export students to Excel"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    from app.services.student_service import student_service
    excel_data = await student_service.export_students_to_excel(class_id, current_user.uid)

    from fastapi.responses import Response
    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=students_{class_id}.xlsx"}
    )