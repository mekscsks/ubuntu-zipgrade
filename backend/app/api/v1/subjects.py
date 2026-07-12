"""
Subjects API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List

from app.schemas import (
    SubjectResponse, SubjectCreate, SubjectUpdate, SuccessResponse
)
from app.services.subject_service import subject_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()


@router.get("", response_model=List[SubjectResponse])
async def list_subjects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """List subjects for current teacher"""
    subjects, total = await subject_service.get_subjects_by_teacher(
        current_user.uid, page, page_size, search
    )
    return subjects


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    subject_data: SubjectCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new subject"""
    subject_data.teacher_id = current_user.uid
    return await subject_service.create_subject(subject_data)


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get subject by ID"""
    subject = await subject_service.get_subject_with_stats(subject_id, current_user.uid)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    update_data: SubjectUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update subject"""
    subject = await subject_service.get_by_id(subject_id)
    if not subject or subject.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Subject not found")
    return await subject_service.update(subject_id, update_data)


@router.delete("/{subject_id}", response_model=SuccessResponse)
async def delete_subject(
    subject_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete (deactivate) subject"""
    subject = await subject_service.get_by_id(subject_id)
    if not subject or subject.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Subject not found")
    await subject_service.update(subject_id, SubjectUpdate(is_active=False))
    return SuccessResponse(message="Subject deleted")


@router.get("/{subject_id}/classes", response_model=List[SubjectResponse])
async def get_subject_classes(
    subject_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get classes for a subject"""
    from app.services.class_service import class_service
    subject = await subject_service.get_by_id(subject_id)
    if not subject or subject.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Subject not found")
    return await class_service.get_classes_by_subject(subject_id, current_user.uid)