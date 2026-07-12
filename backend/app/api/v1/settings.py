"""
Settings API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.schemas import TeacherSettings, SettingsUpdate, SuccessResponse
from app.services.settings_service import settings_service
from app.services.teacher_service import teacher_service
from app.utils.auth import get_current_user, TokenData
from app.firebase.init_firebase import get_storage_bucket

router = APIRouter()


@router.get("", response_model=TeacherSettings)
async def get_settings(current_user: TokenData = Depends(get_current_user)):
    """Get teacher settings"""
    return await settings_service.get_settings(current_user.uid)


@router.put("", response_model=TeacherSettings)
async def update_settings(
    update: SettingsUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update teacher settings"""
    return await settings_service.update_settings(current_user.uid, update)


@router.post("/reset", response_model=TeacherSettings)
async def reset_settings(current_user: TokenData = Depends(get_current_user)):
    """Reset settings to defaults"""
    return await settings_service.reset_settings(current_user.uid)


@router.post("/logo", response_model=SuccessResponse)
async def upload_school_logo(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Upload school logo to Firebase Storage"""
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 2MB)")

    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(f"logos/{current_user.uid}/{file.filename}")
        blob.upload_from_string(content, content_type=file.content_type)
        blob.make_public()
        url = blob.public_url

        # Update settings with logo URL
        await settings_service.update_settings(current_user.uid, SettingsUpdate(school_logo_url=url))
        # Also update teacher profile
        from app.schemas import TeacherUpdate
        await teacher_service.update_teacher(current_user.uid, TeacherUpdate(school_logo_url=url))

        return SuccessResponse(message="Logo uploaded", data={"url": url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
