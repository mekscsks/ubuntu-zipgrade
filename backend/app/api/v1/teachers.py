"""
Teacher API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List

from app.schemas import (
    TeacherResponse, TeacherUpdate, TeacherSettings, SettingsUpdate,
    SuccessResponse, PaginatedResponse
)
from app.services.teacher_service import teacher_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()


@router.get("/me", response_model=TeacherResponse)
async def get_my_profile(current_user: TokenData = Depends(get_current_user)):
    """Get current teacher's profile"""
    teacher = await teacher_service.get_by_uid(current_user.uid)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.put("/me", response_model=TeacherResponse)
async def update_my_profile(
    update_data: TeacherUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update current teacher's profile"""
    teacher = await teacher_service.update_teacher(current_user.uid, update_data)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.get("/me/settings", response_model=TeacherSettings)
async def get_my_settings(current_user: TokenData = Depends(get_current_user)):
    """Get current teacher's settings"""
    return await teacher_service.get_settings(current_user.uid)


@router.put("/me/settings", response_model=TeacherSettings)
async def update_my_settings(
    settings: SettingsUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update current teacher's settings"""
    teacher_settings = TeacherSettings(**settings.model_dump(exclude_unset=True))
    return await teacher_service.update_settings(current_user.uid, teacher_settings)


@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: TokenData = Depends(get_current_user)):
    """Get dashboard statistics"""
    return await teacher_service.get_dashboard_stats(current_user.uid)


@router.delete("/me", response_model=SuccessResponse)
async def deactivate_account(current_user: TokenData = Depends(get_current_user)):
    """Deactivate teacher account"""
    await teacher_service.deactivate_teacher(current_user.uid)
    return SuccessResponse(message="Account deactivated")