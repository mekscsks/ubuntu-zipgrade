"""
Application Configuration Module
Centralized configuration management using Pydantic Settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App Info
    app_name: str = "AI Exam Checker"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # Firebase Admin SDK
    firebase_project_id: str
    firebase_private_key_id: str
    firebase_private_key: str
    firebase_client_email: str
    firebase_client_id: str
    firebase_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    firebase_token_uri: str = "https://oauth2.googleapis.com/token"
    firebase_auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    firebase_client_x509_cert_url: str

    # Firebase Web Config (for frontend)
    firebase_api_key: str
    firebase_auth_domain: str
    firebase_storage_bucket: str
    firebase_messaging_sender_id: str
    firebase_app_id: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8080"])

    # Scanner Settings
    scanner_confidence_threshold: float = 0.7
    scanner_bubble_min_area: int = 50
    scanner_bubble_max_area: int = 500
    scanner_perspective_width: int = 1200
    scanner_perspective_height: int = 1600

    # File Upload
    max_file_size: int = 10485760
    allowed_extensions: List[str] = Field(default_factory=lambda: ["jpg", "jpeg", "png", "pdf"])

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def firebase_credentials_dict(self) -> dict:
        """Return Firebase credentials as dictionary for firebase-admin initialization"""
        return {
            "type": "service_account",
            "project_id": self.firebase_project_id,
            "private_key_id": self.firebase_private_key_id,
            "private_key": self.firebase_private_key.replace("\\n", "\n"),
            "client_email": self.firebase_client_email,
            "client_id": self.firebase_client_id,
            "auth_uri": self.firebase_auth_uri,
            "token_uri": self.firebase_token_uri,
            "auth_provider_x509_cert_url": self.firebase_auth_provider_x509_cert_url,
            "client_x509_cert_url": self.firebase_client_x509_cert_url,
        }

    @property
    def firebase_web_config(self) -> dict:
        """Return Firebase web config for frontend"""
        return {
            "apiKey": self.firebase_api_key,
            "authDomain": self.firebase_auth_domain,
            "projectId": self.firebase_project_id,
            "storageBucket": self.firebase_storage_bucket,
            "messagingSenderId": self.firebase_messaging_sender_id,
            "appId": self.firebase_app_id,
        }


# Global settings instance
settings = Settings()