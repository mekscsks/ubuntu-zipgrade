"""
Pydantic Schemas for Data Validation and Serialization
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    TEACHER = "teacher"
    ADMIN = "admin"
    ASSISTANT = "assistant"


class ExamStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ScanStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"


class PaperSize(str, Enum):
    A4 = "A4"
    LEGAL = "Legal"
    LETTER = "Letter"


# Base Models
class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IDMixin(BaseModel):
    id: str = Field(..., description="Unique identifier")


# Teacher Schemas
class TeacherBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    school_name: Optional[str] = Field(None, max_length=200)
    school_logo_url: Optional[str] = None
    role: UserRole = UserRole.TEACHER


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    school_name: Optional[str] = Field(None, max_length=200)
    school_logo_url: Optional[str] = None
    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    dark_mode: Optional[bool] = None
    passing_percentage: Optional[float] = Field(None, ge=0, le=100)
    paper_size: Optional[PaperSize] = None
    bubble_size: Optional[str] = Field(None, pattern="^(small|medium|large)$")
    scan_sensitivity: Optional[float] = Field(None, ge=0.1, le=1.0)


class TeacherResponse(TeacherBase, IDMixin, TimestampMixin):
    uid: str
    is_active: bool = True
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Student Schemas
class StudentBase(BaseModel):
    student_number: str = Field(..., min_length=1, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    section: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=20)
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    parent_name: Optional[str] = Field(None, max_length=100)
    parent_phone: Optional[str] = Field(None, max_length=20)
    parent_email: Optional[EmailStr] = None


class StudentCreate(StudentBase):
    class_id: str
    teacher_id: str = ""


class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    section: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=20)
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    parent_name: Optional[str] = Field(None, max_length=100)
    parent_phone: Optional[str] = Field(None, max_length=20)
    parent_email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class StudentResponse(StudentBase, IDMixin, TimestampMixin):
    class_id: str
    teacher_id: str
    qr_code_url: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class StudentImportRow(BaseModel):
    student_number: str
    first_name: str
    last_name: str
    section: Optional[str] = None
    grade: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None


# Subject Schemas
class SubjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class SubjectCreate(SubjectBase):
    teacher_id: str = ""


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None


class SubjectResponse(SubjectBase, IDMixin, TimestampMixin):
    teacher_id: str
    is_active: bool = True
    total_exams: int = 0
    total_classes: int = 0

    class Config:
        from_attributes = True


# Class Schemas
class ClassBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    section: str = Field(..., min_length=1, max_length=50)
    grade_level: str = Field(..., min_length=1, max_length=20)
    subject_id: str
    description: Optional[str] = Field(None, max_length=500)
    schedule: Optional[str] = Field(None, max_length=200)
    room: Optional[str] = Field(None, max_length=50)
    max_students: Optional[int] = Field(None, ge=1, le=100)


class ClassCreate(ClassBase):
    teacher_id: str = ""


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    section: Optional[str] = Field(None, min_length=1, max_length=50)
    grade_level: Optional[str] = Field(None, min_length=1, max_length=20)
    subject_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    schedule: Optional[str] = Field(None, max_length=200)
    room: Optional[str] = Field(None, max_length=50)
    max_students: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None


class ClassResponse(ClassBase, IDMixin, TimestampMixin):
    teacher_id: str
    student_count: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


# Exam Schemas
class ExamBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    instructions: Optional[str] = Field(None, max_length=2000)
    subject_id: str
    class_id: str
    num_questions: int = Field(..., ge=1, le=200)
    passing_score: float = Field(..., ge=0, le=100)
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    status: ExamStatus = ExamStatus.DRAFT
    allow_multiple_answers: bool = False
    shuffle_questions: bool = False
    shuffle_options: bool = False
    show_results_immediately: bool = True
    paper_size: PaperSize = PaperSize.A4


class ExamCreate(ExamBase):
    teacher_id: str = ""
    answer_key: List[str] = Field(..., description="List of correct answers (A, B, C, D, E)")


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    instructions: Optional[str] = Field(None, max_length=2000)
    subject_id: Optional[str] = None
    class_id: Optional[str] = None
    num_questions: Optional[int] = Field(None, ge=1, le=200)
    passing_score: Optional[float] = Field(None, ge=0, le=100)
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    status: Optional[ExamStatus] = None
    allow_multiple_answers: Optional[bool] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    show_results_immediately: Optional[bool] = None
    paper_size: Optional[PaperSize] = None
    answer_key: Optional[List[str]] = None


class ExamResponse(ExamBase, IDMixin, TimestampMixin):
    teacher_id: str
    answer_key: List[str]
    total_scans: int = 0
    average_score: Optional[float] = None
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None
    passing_rate: Optional[float] = None

    class Config:
        from_attributes = True


# Answer Key Schema
class AnswerKeyCreate(BaseModel):
    exam_id: str
    answers: List[str] = Field(..., min_length=1, max_length=200)
    version: str = Field(default="A", pattern="^[A-D]$")


class AnswerKeyResponse(AnswerKeyCreate, IDMixin, TimestampMixin):
    pass


# Result Schemas
class QuestionResult(BaseModel):
    question_number: int
    student_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool
    is_blank: bool = False
    has_multiple_marks: bool = False
    confidence: float = Field(default=1.0, ge=0, le=1)


class ScanResultBase(BaseModel):
    exam_id: str
    student_id: str
    class_id: str
    teacher_id: str
    sheet_id: str
    total_questions: int
    correct_count: int
    wrong_count: int
    blank_count: int
    multiple_marks_count: int
    percentage: float = Field(..., ge=0, le=100)
    passed: bool
    question_results: List[QuestionResult]
    scan_confidence: float = Field(default=1.0, ge=0, le=1)
    processing_time_ms: int
    image_url: Optional[str] = None
    status: ScanStatus = ScanStatus.COMPLETED
    reviewed_by_teacher: bool = False
    review_notes: Optional[str] = None


class ScanResultCreate(ScanResultBase):
    pass


class ScanResultResponse(ScanResultBase, IDMixin, TimestampMixin):
    student_name: Optional[str] = None
    student_number: Optional[str] = None

    class Config:
        from_attributes = True


# Scan History Schemas
class ScanHistoryBase(BaseModel):
    exam_id: str
    student_id: str
    class_id: str
    teacher_id: str
    sheet_id: str
    result_id: Optional[str] = None
    status: ScanStatus = ScanStatus.PENDING
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


class ScanHistoryCreate(ScanHistoryBase):
    pass


class ScanHistoryResponse(ScanHistoryBase, IDMixin, TimestampMixin):
    student_name: Optional[str] = None
    student_number: Optional[str] = None
    exam_title: Optional[str] = None
    percentage: Optional[float] = None
    passed: Optional[bool] = None

    class Config:
        from_attributes = True


# Analytics Schemas
class QuestionAnalytics(BaseModel):
    question_number: int
    correct_count: int
    wrong_count: int
    blank_count: int
    multiple_marks_count: int
    difficulty_index: float = Field(..., ge=0, le=1)
    discrimination_index: Optional[float] = None
    option_distribution: Dict[str, int] = Field(default_factory=dict)


class ExamAnalytics(BaseModel):
    exam_id: str
    exam_title: str
    total_students: int
    total_scanned: int
    average_score: float
    highest_score: float
    lowest_score: float
    passing_rate: float
    score_distribution: Dict[str, int] = Field(default_factory=dict)
    question_analytics: List[QuestionAnalytics] = Field(default_factory=list)
    class_rankings: List[Dict[str, Any]] = Field(default_factory=list)
    student_rankings: List[Dict[str, Any]] = Field(default_factory=list)


class ClassAnalytics(BaseModel):
    class_id: str
    class_name: str
    total_students: int
    total_exams: int
    average_score: float
    passing_rate: float
    top_students: List[Dict[str, Any]] = Field(default_factory=list)
    struggling_students: List[Dict[str, Any]] = Field(default_factory=list)


class StudentAnalytics(BaseModel):
    student_id: str
    student_name: str
    student_number: str
    total_exams: int
    exams_taken: int
    average_score: float
    highest_score: float
    lowest_score: float
    passing_rate: float
    score_trend: List[Dict[str, Any]] = Field(default_factory=list)
    subject_performance: List[Dict[str, Any]] = Field(default_factory=list)
    rank_in_class: Optional[int] = None


# Report Schemas
class ReportExportRequest(BaseModel):
    exam_ids: Optional[List[str]] = None
    class_ids: Optional[List[str]] = None
    student_ids: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    format: Literal["excel", "csv", "pdf"] = "excel"
    report_type: Literal["individual", "class", "exam_summary", "question_analysis"] = "exam_summary"


class ReportExportResponse(BaseModel):
    download_url: str
    expires_at: datetime
    file_size: int


# Dashboard Schemas
class DashboardStats(BaseModel):
    total_students: int
    total_classes: int
    total_subjects: int
    total_exams: int
    average_score: float
    total_scans_today: int
    pending_reviews: int
    recent_exams: List[ExamResponse] = Field(default_factory=list)
    recent_scans: List[ScanHistoryResponse] = Field(default_factory=list)


class ChartDataPoint(BaseModel):
    label: str
    value: float
    color: Optional[str] = None


class ChartDataset(BaseModel):
    label: str
    data: List[float]
    background_color: Optional[List[str]] = None
    border_color: Optional[List[str]] = None


class ChartResponse(BaseModel):
    labels: List[str]
    datasets: List[ChartDataset]


# Pagination
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# QR Code Data
class QRCodeData(BaseModel):
    student_id: str
    exam_id: str
    sheet_id: str
    class_id: str
    teacher_id: str
    version: str = "1"


# Settings
class TeacherSettings(BaseModel):
    school_name: str = "My School"
    school_logo_url: Optional[str] = None
    theme: Literal["light", "dark", "system"] = "system"
    dark_mode: bool = False
    passing_percentage: float = 60.0
    paper_size: PaperSize = PaperSize.A4
    bubble_size: Literal["small", "medium", "large"] = "medium"
    scan_sensitivity: float = 0.7
    email_notifications: bool = True
    scan_sound_enabled: bool = True
    auto_save_results: bool = True


class SettingsUpdate(BaseModel):
    school_name: Optional[str] = None
    school_logo_url: Optional[str] = None
    theme: Optional[Literal["light", "dark", "system"]] = None
    dark_mode: Optional[bool] = None
    passing_percentage: Optional[float] = Field(None, ge=0, le=100)
    paper_size: Optional[PaperSize] = None
    bubble_size: Optional[Literal["small", "medium", "large"]] = None
    scan_sensitivity: Optional[float] = Field(None, ge=0.1, le=1.0)
    email_notifications: Optional[bool] = None
    scan_sound_enabled: Optional[bool] = None
    auto_save_results: Optional[bool] = None


# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    uid: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    school_name: Optional[str] = Field(None, max_length=200)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# File Upload
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    url: str
    size: int
    content_type: str


# Error Responses
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


# WebSocket Messages (for real-time scanning)
class ScanProgressMessage(BaseModel):
    type: Literal["progress", "result", "error", "complete"]
    scan_id: str
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[ScanResultResponse] = None
    error: Optional[str] = None