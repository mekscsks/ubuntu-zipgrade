"""
Firebase Initialization Module
Initializes Firebase Admin SDK and provides database/storage clients
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.storage import Bucket
from types import ModuleType
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None
_db: Optional[FirestoreClient] = None
_bucket: Optional[Bucket] = None


def initialize_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin SDK"""
    global _firebase_app, _db, _bucket

    if _firebase_app is not None:
        return _firebase_app

    try:
        cred = credentials.Certificate(settings.firebase_credentials_dict)
        _firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': settings.firebase_storage_bucket
        })
        _db = firestore.client()
        _bucket = storage.bucket()
        logger.info("Firebase initialized successfully")
        return _firebase_app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


def get_firestore_client() -> Optional[FirestoreClient]:
    """Get Firestore client instance"""
    global _db
    if _db is None:
        initialize_firebase()
    return _db


def get_storage_bucket() -> Optional[Bucket]:
    """Get Firebase Storage bucket instance"""
    global _bucket
    if _bucket is None:
        initialize_firebase()
    return _bucket


def get_auth_client() -> ModuleType:
    """Get Firebase Auth client instance"""
    initialize_firebase()
    return auth


def close_firebase():
    """Close Firebase connections"""
    global _firebase_app, _db, _bucket
    if _firebase_app:
        firebase_admin.delete_app(_firebase_app)
        _firebase_app = None
        _db = None
        _bucket = None
        logger.info("Firebase connections closed")


# Collection references
class Collections:
    """Firestore collection names"""
    TEACHERS = "teachers"
    STUDENTS = "students"
    SUBJECTS = "subjects"
    CLASSES = "classes"
    EXAMS = "exams"
    ANSWER_KEYS = "answer_keys"
    RESULTS = "results"
    SCAN_HISTORY = "scan_history"
    SETTINGS = "settings"