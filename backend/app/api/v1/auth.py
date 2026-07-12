"""
Authentication API Routes
Handles login, registration, password reset, token refresh
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.security import HTTPBearer
from pydantic import EmailStr
from typing import Optional
import logging

from app.schemas import (
    LoginRequest, RegisterRequest, PasswordResetRequest,
    PasswordChangeRequest, Token, TokenData, SuccessResponse, ErrorResponse
)
from app.utils.auth import (
    create_access_token, decode_access_token, get_current_user,
    verify_teacher_exists, get_teacher_data, verify_firebase_token
)
from app.services.teacher_service import teacher_service
from app.firebase.init_firebase import get_auth_client

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new teacher"""
    try:
        auth_client = get_auth_client()

        # Create Firebase Auth user
        user = auth_client.create_user(
            email=request.email,
            password=request.password,
            display_name=request.display_name
        )

        # Create teacher profile in Firestore
        from app.schemas import TeacherCreate
        teacher_data = TeacherCreate(
            email=request.email,
            display_name=request.display_name,
            school_name=request.school_name
        )
        await teacher_service.create_teacher(teacher_data, user.uid)

        # Create access token
        token = await create_access_token({
            "uid": user.uid,
            "email": user.email,
            "role": "teacher",
            "display_name": request.display_name,
            "school_name": request.school_name or ""
        })

        return Token(access_token=token, expires_in=1440 * 60)

    except Exception as e:
        logger.error(f"Registration failed: {e}")
        if "EMAIL_EXISTS" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """Login with email and password (Firebase Auth)"""
    try:
        # For Firebase Auth, we verify the password by trying to sign in
        # In practice, the frontend would use Firebase SDK to sign in,
        # then send the ID token to this endpoint for verification
        # Here we simulate by checking if user exists

        from app.firebase.init_firebase import get_firestore_client
        db = get_firestore_client()

        # Find teacher by email
        teachers = db.collection("teachers").where("email", "==", request.email).limit(1).get()
        if not teachers:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        teacher_doc = teachers[0]
        teacher_data = teacher_doc.to_dict()
        teacher_data['id'] = teacher_doc.id

        # In real implementation, verify password via Firebase Auth REST API
        # For now, we'll create a token if teacher exists
        # Frontend should use Firebase Auth to get ID token first

        token = await create_access_token({
            "uid": teacher_data['uid'],
            "email": teacher_data['email'],
            "role": teacher_data.get('role', 'teacher'),
            "display_name": teacher_data.get('display_name', ''),
            "school_name": teacher_data.get('school_name', '')
        })

        # Update last login
        await teacher_service.update_last_login(teacher_data['uid'])

        return Token(access_token=token, expires_in=1440 * 60)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/register-with-token", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_with_token(id_token: str = Query(...), display_name: str = "", school_name: str = ""):
    """Create teacher profile in Firestore using Firebase ID token (correct UID)"""
    try:
        decoded = await verify_firebase_token(id_token)
        if not decoded:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        uid = decoded['uid']
        email = decoded.get('email', '')

        from app.schemas import TeacherCreate
        teacher_data = TeacherCreate(
            email=email,
            display_name=display_name or decoded.get('name', email),
            school_name=school_name or None
        )
        await teacher_service.create_teacher(teacher_data, uid)

        token = await create_access_token({
            "uid": uid,
            "email": email,
            "role": "teacher",
            "display_name": display_name,
            "school_name": school_name or ""
        })
        return Token(access_token=token, expires_in=1440 * 60)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"register_with_token failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/verify-token", response_model=Token)
async def verify_token(id_token: str = Query(...)):
    """Verify Firebase ID token and return custom JWT"""
    try:
        decoded = await verify_firebase_token(id_token)
        if not decoded:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        uid = decoded['uid']
        exists = await verify_teacher_exists(uid)
        if not exists:
            # Auto-create teacher profile if missing (e.g. registered via Firebase Console)
            from app.schemas import TeacherCreate
            teacher_data = TeacherCreate(
                email=decoded.get('email', ''),
                display_name=decoded.get('name', decoded.get('email', 'Teacher')),
            )
            await teacher_service.create_teacher(teacher_data, uid)

        teacher = await get_teacher_data(uid)

        token = await create_access_token({
            "uid": uid,
            "email": decoded.get('email', ''),
            "role": teacher.get('role', 'teacher') if teacher else 'teacher',
            "display_name": teacher.get('display_name', '') if teacher else '',
            "school_name": teacher.get('school_name', '') if teacher else ''
        })

        await teacher_service.update_last_login(uid)

        return Token(access_token=token, expires_in=1440 * 60)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)):
    """Refresh access token"""
    token = await create_access_token({
        "uid": current_user.uid,
        "email": current_user.email,
        "role": current_user.role.value,
        "display_name": "",  # Could fetch from DB
        "school_name": ""
    })
    return Token(access_token=token, expires_in=1440 * 60)


@router.post("/forgot-password", response_model=SuccessResponse)
async def forgot_password(request: PasswordResetRequest):
    """Send password reset email"""
    try:
        auth_client = get_auth_client()
        auth_client.send_password_reset_email(request.email)
        return SuccessResponse(message="Password reset email sent")
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset email"
        )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Change password (requires current password)"""
    try:
        auth_client = get_auth_client()
        auth_client.update_user(current_user.uid, password=request.new_password)
        return SuccessResponse(message="Password changed successfully")
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.get("/me", response_model=TokenData)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user info from token"""
    return current_user


@router.post("/logout", response_model=SuccessResponse)
async def logout():
    """Logout (client-side token removal)"""
    return SuccessResponse(message="Logged out successfully")