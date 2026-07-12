"""
Authentication Module
Handles JWT token creation, validation, and Firebase Auth integration
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.config import settings
from app.firebase.init_firebase import get_auth_client
from app.schemas import TokenData, UserRole

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate JWT access token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        uid: str = payload.get("uid")
        email: str = payload.get("email")
        role: str = payload.get("role", "teacher")
        if uid is None:
            return None
        return TokenData(uid=uid, email=email, role=UserRole(role))
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None


async def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """Verify Firebase ID token"""
    try:
        auth_client = get_auth_client()
        decoded_token = auth_client.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception

    return token_data


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current active user (alias for get_current_user)"""
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None
    return decode_access_token(credentials.credentials)


def require_role(allowed_roles: list[UserRole]):
    """Dependency to require specific roles"""
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


# Teacher authentication helpers
async def create_teacher_token(teacher_data: Dict[str, Any]) -> str:
    """Create access token for teacher"""
    token_data = {
        "uid": teacher_data["uid"],
        "email": teacher_data["email"],
        "role": teacher_data.get("role", "teacher"),
        "display_name": teacher_data.get("display_name", ""),
        "school_name": teacher_data.get("school_name", ""),
    }
    return create_access_token(token_data)


async def verify_teacher_exists(uid: str) -> bool:
    """Verify teacher exists in Firestore"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()
    doc = db.collection("teachers").document(uid).get()
    return doc.exists


async def get_teacher_data(uid: str) -> Optional[Dict[str, Any]]:
    """Get teacher data from Firestore"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()
    doc = db.collection("teachers").document(uid).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None