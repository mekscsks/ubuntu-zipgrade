# AI Exam Checker - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Expanded Project Structure](#expanded-project-structure)
4. [Installation Guide](#installation-guide)
5. [Environment Variables](#environment-variables)
6. [Firebase Setup](#firebase-setup)
7. [Database Design](#database-design)
8. [Firestore Relationship Diagram](#firestore-relationship-diagram)
9. [API Documentation](#api-documentation)
10. [Standard REST API Response Format](#standard-rest-api-response-format)
11. [OMR Answer Sheet Specification](#omr-answer-sheet-specification)
12. [Scanner Workflow](#scanner-workflow)
13. [OMR Scanner Technical Design](#omr-scanner-technical-design)
14. [Scanner Performance Targets](#scanner-performance-targets)
15. [Deployment Guide](#deployment-guide)
16. [Logging Strategy](#logging-strategy)
17. [Backup and Recovery Plan](#backup-and-recovery-plan)
18. [Testing Plan](#testing-plan)
19. [Developer Notes](#developer-notes)

---

## Overview

AI Exam Checker is a production-ready web application for teachers to create exams, generate printable bubble-sheet answer sheets, scan completed sheets using a mobile camera, automatically grade answers using OpenCV, and generate analytics.

**Tech Stack:**
- Frontend: HTML5, Tailwind CSS, Vanilla JS (ES6 Modules)
- Backend: Python 3.11+, FastAPI
- Image Processing: OpenCV, NumPy, pyzbar
- Auth: Firebase Authentication + JWT
- Database: Firebase Firestore
- Storage: Firebase Storage
- Deployment: Frontend → Vercel, Backend → Railway/Render

---

## Project Structure

```
ai exam checker/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── config.py              # Pydantic settings
│       ├── api/v1/
│       │   ├── __init__.py        # Router aggregation
│       │   ├── auth.py            # Login, register, token
│       │   ├── teachers.py        # Teacher profile
│       │   ├── subjects.py        # Subject CRUD
│       │   ├── classes.py         # Class CRUD + student import
│       │   ├── students.py        # Student CRUD
│       │   ├── exams.py           # Exam CRUD + answer sheets
│       │   ├── scanner.py         # Image processing endpoint
│       │   ├── results.py         # Scan results + review
│       │   ├── dashboard.py       # Stats + charts
│       │   ├── reports.py         # Excel/CSV/PDF export
│       │   └── settings.py        # Teacher settings
│       ├── firebase/
│       │   └── init_firebase.py   # Firebase Admin SDK init
│       ├── scanner/
│       │   └── scanner_service.py # OpenCV pipeline + PDF generator
│       ├── schemas/__init__.py    # All Pydantic models
│       ├── services/
│       │   ├── base_service.py    # Generic Firestore CRUD
│       │   ├── teacher_service.py
│       │   ├── subject_service.py
│       │   ├── class_service.py
│       │   ├── student_service.py
│       │   ├── exam_service.py
│       │   ├── result_service.py
│       │   ├── scan_history_service.py
│       │   └── settings_service.py
│       └── utils/auth.py          # JWT + Firebase token helpers
└── frontend/
    ├── index.html                 # Root redirect + PWA entry
    ├── manifest.json              # PWA manifest
    ├── sw.js                      # Service worker
    ├── assets/
    │   ├── css/main.css           # Global styles
    │   └── js/
    │       ├── api.js             # API client + all endpoints
    │       ├── auth.js            # Firebase auth module
    │       └── ui.js              # Toast, modal, pagination utils
    ├── components/
    │   └── layout.js              # Sidebar + header component
    └── pages/
        ├── login.html
        ├── register.html
        ├── forgot-password.html
        ├── dashboard.html
        ├── subjects.html
        ├── classes.html
        ├── students.html
        ├── exams.html             # Includes answer key builder
        ├── scanner.html           # Camera scanner + manual review
        ├── scan-history.html
        ├── analytics.html
        ├── reports.html
        └── settings.html
```

---

## Expanded Project Structure

The tree above covers the core application code. In addition to those files, a production deployment introduces several supporting folders. These are not part of the application source tree that gets imported by Python/JS, but they are part of the working repository/runtime environment and should be created (and gitignored where noted) alongside `backend/` and `frontend/`.

```
ai exam checker/
├── backend/
│   ├── ... (see Project Structure above)
│   ├── tests/                      # Automated test suite (see Testing Plan)
│   │   ├── unit/                   # Unit tests for services/utils
│   │   ├── integration/            # API endpoint tests (FastAPI TestClient)
│   │   ├── scanner/                # OMR accuracy tests against sample sheets
│   │   ├── fixtures/                # Sample images, mock Firestore data
│   │   └── conftest.py             # Pytest fixtures (test client, mock auth)
│   ├── logs/                       # Rotating log files (gitignored)
│   │   ├── api.log
│   │   ├── scanner.log
│   │   ├── auth.log
│   │   └── error.log
│   ├── scripts/                    # One-off / maintenance scripts
│   │   ├── seed_demo_data.py       # Populate Firestore with demo teacher/classes
│   │   ├── backup_firestore.py     # Manual Firestore export trigger
│   │   ├── cleanup_temp_uploads.py # Cron job: purge stale temp files
│   │   └── generate_sample_sheets.py
│   ├── storage/                    # Local filesystem storage (gitignored)
│   │   ├── temp_uploads/           # Scanned images awaiting processing
│   │   └── generated_pdfs/         # Answer sheet PDFs (cached before Firebase Storage upload)
│   └── docs/                        # (this folder) architecture + API reference
└── frontend/
    ├── ... (see Project Structure above)
    └── assets/
        └── icons/                  # PWA icons (192x192, 512x512, maskable)
```

### Folder Purposes

| Folder | Purpose |
|--------|---------|
| `backend/tests/` | Houses all automated tests described in the [Testing Plan](#testing-plan). Split by test type so `pytest tests/unit` or `pytest tests/scanner` can run independently in CI. |
| `backend/logs/` | Destination for the rotating log files defined in the [Logging Strategy](#logging-strategy). Gitignored; regenerated at runtime. |
| `backend/scripts/` | Standalone maintenance and operations scripts that are run manually or via cron/scheduled task, not imported by the FastAPI app itself. |
| `backend/storage/temp_uploads/` | Short-lived holding area for images uploaded to `/scan/process` before/while they are processed. Cleaned up automatically after processing (see `TEMP_UPLOAD_PATH`). |
| `backend/storage/generated_pdfs/` | Local cache of generated answer-sheet PDFs before (or instead of) upload to Firebase Storage. Useful for batch generation jobs (see `PDF_OUTPUT_PATH`). |
| `docs/` | Project documentation, including this file. |
| `frontend/assets/icons/` | PWA icon set referenced by `manifest.json` (currently empty — see Known Limitations). |

> **Note:** `logs/`, `storage/temp_uploads/`, and `storage/generated_pdfs/` should all be added to `.gitignore`. They are runtime artifacts, not source code.

---

## Installation Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ (for local dev server)
- Firebase project with Firestore, Auth, and Storage enabled

### Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Copy and fill environment variables
cp .env.example .env
# Edit .env with your Firebase credentials and JWT secret

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

The frontend is pure HTML/CSS/JS with no build step required.

```bash
# Option 1: VS Code Live Server extension (recommended)
# Open frontend/ folder and click "Go Live"

# Option 2: Python simple server
cd frontend
python -m http.server 3000

# Option 3: npx serve
npx serve frontend -p 3000
```

**Update Firebase config** in each HTML page's `<script>` block:
```javascript
window.APP_CONFIG = {
  apiBase: 'http://localhost:8000/api/v1',
  firebase: {
    apiKey: "YOUR_ACTUAL_API_KEY",
    authDomain: "your-project.firebaseapp.com",
    projectId: "your-project-id",
    storageBucket: "your-project.appspot.com",
    messagingSenderId: "123456789",
    appId: "1:123456789:web:abcdef"
  }
};
```

---

## Environment Variables

This expands on the variables already shown in `backend/.env.example`. The Firebase, JWT, application, CORS, scanner, upload, and pagination variables already documented in the Installation Guide remain unchanged. The variables below are additional settings that should be added to `.env.example` and `.env` to support uploads, PDF generation, logging, and scan behavior described elsewhere in this document.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_UPLOAD_SIZE` | int (bytes) | `10485760` (10 MB) | Hard limit on the size of a single uploaded scan image. Requests exceeding this are rejected with `413 Payload Too Large` before image processing begins. (Equivalent in purpose to the existing `MAX_FILE_SIZE`; use one consistently.) |
| `SCAN_TIMEOUT` | int (seconds) | `15` | Maximum time the OpenCV pipeline is allowed to run on a single image before it is aborted and a timeout error is returned. Prevents a malformed or adversarial image from hanging a worker. |
| `TEMP_UPLOAD_PATH` | string (path) | `./storage/temp_uploads` | Filesystem path where incoming scan images are temporarily written before/while being processed. Cleared automatically after processing completes or fails; also swept periodically by `scripts/cleanup_temp_uploads.py`. |
| `PDF_OUTPUT_PATH` | string (path) | `./storage/generated_pdfs` | Filesystem path where generated answer-sheet PDFs are written before being served or uploaded to Firebase Storage. Used by the batch answer-sheet generation endpoints. |
| `LOG_LEVEL` | string (enum) | `INFO` | Minimum severity written to log files/stdout. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. See [Logging Strategy](#logging-strategy). |
| `IMAGE_MAX_RESOLUTION` | string (`WxH`) | `2000x2600` | Incoming images larger than this are downscaled (preserving aspect ratio) before processing, to keep OpenCV processing time predictable. |
| `DEFAULT_PAPER_SIZE` | string (enum) | `A4` | Default paper size (`A4` or `Legal`) applied to new exams/answer sheets when the teacher does not explicitly choose one. See [OMR Answer Sheet Specification](#omr-answer-sheet-specification). |
| `AUTO_SAVE_RESULTS` | boolean | `true` | When `true`, scan results with confidence ≥ `SCANNER_CONFIDENCE_THRESHOLD` are saved to Firestore immediately. When `false`, all results (regardless of confidence) are held in a pending state until the teacher confirms them in Manual Review. Mirrors the per-teacher `auto_save_results` field already present in the `settings/{teacher_uid}` document; the env var defines the system-wide default for new teacher accounts. |

**Example additions to `.env.example`:**
```
# Upload & Processing
MAX_UPLOAD_SIZE=10485760
SCAN_TIMEOUT=15
TEMP_UPLOAD_PATH=./storage/temp_uploads
PDF_OUTPUT_PATH=./storage/generated_pdfs
IMAGE_MAX_RESOLUTION=2000x2600
DEFAULT_PAPER_SIZE=A4
AUTO_SAVE_RESULTS=true

# Logging
LOG_LEVEL=INFO
```

---

## Firebase Setup

### 1. Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create new project
3. Enable **Authentication** → Email/Password provider
4. Enable **Firestore Database** → Start in production mode
5. Enable **Storage**

### 2. Service Account (Backend)
1. Project Settings → Service Accounts → Generate new private key
2. Copy values to `.env` file

### 3. Firestore Security Rules
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Teachers can only access their own data
    match /teachers/{teacherId} {
      allow read, write: if request.auth != null && request.auth.uid == teacherId;
    }
    match /students/{studentId} {
      allow read, write: if request.auth != null &&
        resource.data.teacher_id == request.auth.uid;
    }
    match /exams/{examId} {
      allow read, write: if request.auth != null &&
        resource.data.teacher_id == request.auth.uid;
    }
    match /results/{resultId} {
      allow read, write: if request.auth != null &&
        resource.data.teacher_id == request.auth.uid;
    }
    match /{collection}/{docId} {
      allow read, write: if request.auth != null &&
        resource.data.teacher_id == request.auth.uid;
    }
  }
}
```

### 4. Storage Rules
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /logos/{teacherId}/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null && request.auth.uid == teacherId;
    }
    match /{allPaths=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

---

## Database Design

### Firestore Collections

#### `teachers/{uid}`
```json
{
  "uid": "firebase_uid",
  "email": "teacher@school.com",
  "display_name": "John Smith",
  "school_name": "My School",
  "school_logo_url": null,
  "role": "teacher",
  "is_active": true,
  "last_login": "timestamp",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### `subjects/{id}`
```json
{
  "name": "Mathematics",
  "code": "MATH101",
  "description": "...",
  "color": "#2563EB",
  "teacher_id": "uid",
  "is_active": true,
  "total_exams": 5,
  "total_classes": 3,
  "created_at": "timestamp"
}
```

#### `classes/{id}`
```json
{
  "name": "Grade 10 - Section A",
  "section": "A",
  "grade_level": "Grade 10",
  "subject_id": "subject_id",
  "teacher_id": "uid",
  "student_count": 35,
  "schedule": "MWF 8:00-9:00",
  "room": "Room 101",
  "max_students": 40,
  "is_active": true
}
```

#### `students/{id}`
```json
{
  "student_number": "2024-001",
  "first_name": "Jane",
  "last_name": "Doe",
  "class_id": "class_id",
  "teacher_id": "uid",
  "section": "A",
  "grade": "Grade 10",
  "email": "jane@school.com",
  "phone": null,
  "parent_name": null,
  "qr_code_url": null,
  "is_active": true
}
```

#### `exams/{id}`
```json
{
  "title": "Midterm Exam Q1",
  "subject_id": "subject_id",
  "class_id": "class_id",
  "teacher_id": "uid",
  "num_questions": 50,
  "passing_score": 60.0,
  "answer_key": ["A","B","C","D","A",...],
  "duration_minutes": 60,
  "paper_size": "A4",
  "status": "published",
  "total_scans": 30,
  "average_score": 72.5,
  "highest_score": 98.0,
  "lowest_score": 42.0,
  "passing_rate": 80.0
}
```

#### `results/{id}`
```json
{
  "exam_id": "exam_id",
  "student_id": "student_id",
  "class_id": "class_id",
  "teacher_id": "uid",
  "sheet_id": "exam_id_student_id",
  "total_questions": 50,
  "correct_count": 38,
  "wrong_count": 10,
  "blank_count": 2,
  "multiple_marks_count": 0,
  "percentage": 76.0,
  "passed": true,
  "question_results": [
    { "question_number": 1, "student_answer": "A", "correct_answer": "A", "is_correct": true, "is_blank": false, "has_multiple_marks": false, "confidence": 0.95 }
  ],
  "scan_confidence": 0.92,
  "processing_time_ms": 1240,
  "status": "completed",
  "reviewed_by_teacher": false
}
```

#### `scan_history/{id}`
```json
{
  "exam_id": "exam_id",
  "student_id": "student_id",
  "class_id": "class_id",
  "teacher_id": "uid",
  "sheet_id": "...",
  "result_id": "result_id",
  "status": "completed",
  "processing_time_ms": 1240,
  "error_message": null
}
```

#### `settings/{teacher_uid}`
```json
{
  "school_name": "My School",
  "school_logo_url": null,
  "theme": "system",
  "dark_mode": false,
  "passing_percentage": 60.0,
  "paper_size": "A4",
  "bubble_size": "medium",
  "scan_sensitivity": 0.7,
  "scan_sound_enabled": true,
  "auto_save_results": true
}
```

---

## Firestore Relationship Diagram

Firestore is a document database, so there are no foreign keys or joins — every relationship below is implemented as a plain string field (e.g. `teacher_id`, `subject_id`) that stores the document ID of the parent. All top-level collections are flat (not subcollections), and every document is scoped to a `teacher_id`, which is also how Firestore Security Rules enforce data isolation (see [Firebase Setup](#firebase-setup)).

```
                              ┌───────────────────┐
                              │  teachers/{uid}    │
                              │  (root of tenancy) │
                              └─────────┬──────────┘
                                        │ teacher_id
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
   ┌─────────────────┐      ┌─────────────────────┐   ┌─────────────────────┐
   │ subjects/{id}    │      │ settings/{teacher_uid}│   │  (all collections    │
   │                  │      │ 1:1 with teacher     │   │   below also carry    │
   └────────┬─────────┘      └──────────────────────┘   │   teacher_id)         │
            │ subject_id                                 └───────────────────────┘
            ▼
   ┌─────────────────┐
   │ classes/{id}     │
   │ (subject_id,     │
   │  teacher_id)     │
   └────────┬─────────┘
            │ class_id
            ▼
   ┌─────────────────┐
   │ students/{id}    │
   │ (class_id,       │
   │  teacher_id)     │
   └────────┬─────────┘
            │ student_id                     ┌─────────────────┐
            │                        class_id │ exams/{id}       │
            │                        ◄────────┤ (subject_id,     │
            │                                 │  class_id,       │
            │                                 │  teacher_id)     │
            │                                 └────────┬─────────┘
            │                                          │ exam_id
            ▼                                          ▼
   ┌───────────────────────────────────────────────────────────┐
   │ results/{id}                                                │
   │ (exam_id, student_id, class_id, teacher_id, sheet_id)       │
   └───────────────────────────┬───────────────────────────────┘
                                │ result_id
                                ▼
                   ┌───────────────────────┐
                   │ scan_history/{id}      │
                   │ (exam_id, student_id,  │
                   │  class_id, result_id,  │
                   │  teacher_id)           │
                   └────────────────────────┘
```

### How Each Collection References the Others

| Collection | References | Referenced By | Notes |
|------------|-----------|----------------|-------|
| `teachers/{uid}` | — (root) | every other collection via `teacher_id` | Document ID **is** the Firebase Auth UID, so no separate `teacher_id` field is needed on this collection itself. |
| `subjects/{id}` | `teacher_id` | `classes.subject_id`, `exams.subject_id` | A subject belongs to exactly one teacher; a teacher has many subjects. |
| `classes/{id}` | `teacher_id`, `subject_id` | `students.class_id`, `exams.class_id` | A class belongs to one subject. Denormalized `student_count` is updated whenever a student is added/removed to avoid a count query. |
| `students/{id}` | `teacher_id`, `class_id` | `results.student_id`, `scan_history.student_id` | Students are scoped to a single class. Re-enrolling a student in a new class updates `class_id` in place rather than creating a new document. |
| `exams/{id}` | `teacher_id`, `subject_id`, `class_id` | `results.exam_id`, `scan_history.exam_id` | Denormalized stats (`total_scans`, `average_score`, `passing_rate`, etc.) are recalculated after every new result to keep dashboard reads cheap. |
| `results/{id}` | `teacher_id`, `exam_id`, `student_id`, `class_id` | `scan_history.result_id` | One result per student per exam (`sheet_id = exam_id_student_id` enforces uniqueness at the application layer). |
| `scan_history/{id}` | `teacher_id`, `exam_id`, `student_id`, `class_id`, `result_id` | — (leaf) | An audit trail of every scan attempt, including failed/low-confidence scans that never produced a saved `result`. |
| `settings/{teacher_uid}` | — (document ID is `teacher_id`) | — (leaf) | 1:1 with `teachers`; stored as a separate collection rather than a subfield so it can be read/written independently without touching the `teachers` document. |

**Composite indexes required** (see [Firestore Setup](#firebase-setup)): `teacher_id + created_at` on `subjects`, `classes`, `students`, `exams`, `results`, and `scan_history` — all list/dashboard queries filter by `teacher_id` and sort by `created_at`.

---

## API Documentation

Base URL: `http://localhost:8000/api/v1`

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new teacher |
| POST | `/auth/login` | Login (returns JWT) |
| POST | `/auth/verify-token` | Exchange Firebase ID token for JWT |
| POST | `/auth/refresh` | Refresh JWT |
| POST | `/auth/forgot-password` | Send reset email |
| POST | `/auth/change-password` | Change password |
| GET | `/auth/me` | Get current user |

### Subjects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/subjects` | List subjects (paginated) |
| POST | `/subjects` | Create subject |
| GET | `/subjects/{id}` | Get subject with stats |
| PUT | `/subjects/{id}` | Update subject |
| DELETE | `/subjects/{id}` | Soft delete subject |

### Classes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/classes` | List classes |
| POST | `/classes` | Create class |
| GET | `/classes/{id}` | Get class with student count |
| PUT | `/classes/{id}` | Update class |
| DELETE | `/classes/{id}` | Soft delete class |
| GET | `/classes/{id}/students` | Get students in class |
| POST | `/students/import?class_id=` | Import students from Excel |
| GET | `/students/export/excel?class_id=` | Export students to Excel |

### Exams
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/exams` | List exams (filter by status/subject/class) |
| POST | `/exams` | Create exam with answer key |
| GET | `/exams/{id}` | Get exam with statistics |
| PUT | `/exams/{id}` | Update exam |
| DELETE | `/exams/{id}` | Archive exam |
| POST | `/exams/{id}/publish` | Publish exam |
| POST | `/exams/{id}/archive` | Archive exam |
| POST | `/exams/{id}/duplicate` | Duplicate exam |
| GET | `/exams/{id}/answer-sheet?student_id=` | Generate PDF answer sheet |
| GET | `/exams/{id}/answer-sheets/batch?class_id=` | Batch generate answer sheets |

### Scanner
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scan/process` | Process uploaded image file |
| POST | `/scan/process-base64` | Process base64 image (camera) |
| GET | `/scan/history` | Get scan history |
| GET | `/scan/history/{id}` | Get scan detail |
| DELETE | `/scan/history/{id}` | Delete scan record |

### Results
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/results/exam/{id}` | Get all results for exam |
| GET | `/results/exam/{id}/statistics` | Get exam statistics |
| GET | `/results/student/{id}` | Get student's results |
| GET | `/results/pending-review` | Get results needing review |
| PUT | `/results/{id}/review` | Submit manual review |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/exam/{id}/excel` | Export exam results as Excel |
| GET | `/reports/exam/{id}/csv` | Export exam results as CSV |
| GET | `/reports/exam/{id}/pdf` | Export exam report as PDF |
| GET | `/reports/student/{id}/excel` | Export student report |
| GET | `/reports/class/{id}/excel` | Export class report |
| GET | `/reports/exam/{id}/question-analysis/excel` | Export question analysis |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/stats` | Get all dashboard statistics |
| GET | `/dashboard/charts/score-distribution` | Score distribution data |
| GET | `/dashboard/charts/score-trend` | Score trend over time |
| GET | `/dashboard/charts/passing-rate` | Passing rate trend |
| GET | `/dashboard/charts/class-performance` | Performance by class |
| GET | `/dashboard/charts/subject-performance` | Performance by subject |

---

## Standard REST API Response Format

Every endpoint under `/api/v1` returns JSON using one of the shapes below. This standardizes error handling on the frontend (`assets/js/api.js` checks `success` before reading `data`) and keeps FastAPI's automatic OpenAPI docs consistent.

### Success Response
```json
{
  "success": true,
  "data": {
    "id": "subj_8f3a2c",
    "name": "Mathematics",
    "code": "MATH101"
  },
  "message": "Subject created successfully"
}
```

### Validation Error (HTTP 422)
```json
{
  "success": false,
  "error": "Validation failed",
  "details": [
    { "field": "email", "message": "value is not a valid email address" },
    { "field": "num_questions", "message": "must be greater than 0" }
  ]
}
```

### Authentication Error (HTTP 401 / 403)
```json
{
  "success": false,
  "error": "Not authenticated",
  "code": "AUTH_TOKEN_INVALID"
}
```
| Code | Meaning |
|------|---------|
| `AUTH_TOKEN_MISSING` | No `Authorization: Bearer <token>` header supplied |
| `AUTH_TOKEN_EXPIRED` | JWT has expired; client should call `/auth/refresh` |
| `AUTH_TOKEN_INVALID` | JWT signature invalid or malformed |
| `AUTH_FORBIDDEN` | Token valid, but the resource belongs to a different `teacher_id` |

### Server Error (HTTP 500)
```json
{
  "success": false,
  "error": "Internal server error"
}
```
Matches the existing global exception handler in `backend/main.py`, which intentionally omits stack traces from the response body and instead logs them server-side (see [Logging Strategy](#logging-strategy)).

### Pagination Response
```json
{
  "success": true,
  "data": [
    { "id": "std_001", "first_name": "Jane", "last_name": "Doe" },
    { "id": "std_002", "first_name": "John", "last_name": "Smith" }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 137,
    "total_pages": 7,
    "has_next": true,
    "has_previous": false
  }
}
```
Governed by the existing `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` settings.

### Upload Response
```json
{
  "success": true,
  "data": {
    "file_id": "upload_9c1b",
    "file_name": "class10a_scan_014.jpg",
    "file_size": 482113,
    "content_type": "image/jpeg",
    "storage_url": "https://storage.googleapis.com/exam-713d5.firebasestorage.app/scans/upload_9c1b.jpg"
  },
  "message": "File uploaded successfully"
}
```

---

## OMR Answer Sheet Specification

This defines the printable answer sheet layout generated by `POST /exams/{id}/answer-sheet` (via `scanner_service.py`'s PDF generator) and consumed by the scanning pipeline. Consistency between generation and scanning is critical — the scanner's bubble-grid detection assumes sheets were produced by this same specification.

### Paper Sizes

| Paper Size | Dimensions | Usable Margin Area |
|------------|-----------|---------------------|
| A4 | 210mm × 297mm | 190mm × 277mm (10mm margins all sides) |
| Legal | 215.9mm × 355.6mm | 195.9mm × 335.6mm (10mm margins all sides) |

Both sizes render at 300 DPI for print (matching the internal warp target of `SCANNER_PERSPECTIVE_WIDTH` / `SCANNER_PERSPECTIVE_HEIGHT` after perspective correction, scaled proportionally).

### Bubble Dimensions & Spacing

| Property | Value | Notes |
|----------|-------|-------|
| Bubble shape | Circle | Ellipses reduce fill-ratio accuracy |
| Bubble diameter | 4.5mm (default), 4.0mm (small), 5.0mm (large) | Configurable via teacher `settings.bubble_size` |
| Bubble stroke width | 0.35mm | Thin enough to avoid being mistaken for a fill |
| Horizontal spacing (option to option) | 8mm center-to-center | Fits 4–5 options per question row |
| Vertical spacing (question to question) | 7mm center-to-center | |
| Option label offset | 2mm to the left of each bubble | Printed letter (A/B/C/D/E) for manual reference |

These correspond directly to `SCANNER_BUBBLE_MIN_AREA` / `SCANNER_BUBBLE_MAX_AREA` in `.env` — those thresholds should be recalculated (`π × radius²` in warped-image pixels) if bubble diameter is changed.

### Margins
- **Outer margin:** 10mm on all four sides (kept clear of any printed content so the paper-detection edge-finding step has a clean, high-contrast border against the scanning surface).
- **Header safe zone:** top 25mm reserved for school logo, exam title, and student info block.
- **Footer safe zone:** bottom 12mm reserved for page number / sheet ID text (human-readable fallback if the QR code fails to scan).

### QR Code Placement
- **Position:** top-right corner, 12mm × 12mm, inset 8mm from the top and right edges.
- **Content:** the JSON payload documented in [Scanner Workflow → QR Code Data Format](#scanner-workflow).
- **Error correction:** Level M (15% damage tolerance) — balances scan reliability against printed size.
- **Quiet zone:** minimum 2mm of white space around the QR code, per QR code spec, to guarantee `pyzbar` detection.

### Student Information Section
Located directly below the header safe zone:
- Printed (pre-filled at generation time, not hand-written): Student Name, Student Number, Class/Section, Exam Title, Date.
- One additional hand-fillable field: **Signature line** (not OCR'd, for manual verification only).
- This section is intentionally *outside* the bubble grid bounding box used by `_detect_bubbles()`, so OCR/handwriting never interferes with bubble detection.

### School Logo Placement
- **Position:** top-left corner, max 20mm × 20mm bounding box.
- **Source:** `school_logo_url` from the `teachers`/`settings` document, fetched at PDF-generation time.
- **Fallback:** if no logo is set, the space collapses and the header safe zone shrinks accordingly — the bubble grid position is computed dynamically, not hardcoded, so this never shifts bubble coordinates.

### Corner Alignment Markers
Four solid black squares (6mm × 6mm), printed 5mm inset from each of the four page corners.
- Used by `_detect_and_warp_paper()` as a fallback/verification when the plain paper-edge contour is ambiguous (e.g., photographed against a white/light background where the page edge itself has low contrast).
- Must remain solid black with no anti-aliasing artifacts in the generated PDF — soft edges reduce corner-detection precision.

### Supported Question Counts
`20, 30, 40, 50, 60, 80, 100, 150, 200`

| Question Count | Layout | Columns |
|-----------------|--------|---------|
| 20 – 50 | Single column | 1 |
| 60 – 100 | Two columns | 2 |
| 150 | Three columns | 3 |
| 200 | Three columns, two-page sheet | 3 (per page) |

### Multi-Column Layout Recommendations
- Split questions **evenly** across columns in reading order (e.g., 100 questions → Q1–50 left column, Q51–100 right column), not interleaved — this matches how students naturally scan the page and simplifies grid-index math in `_detect_bubbles()`.
- Minimum 10mm gutter between columns, printed as a thin (0.2mm) vertical divider line to aid visual (not algorithmic) separation for the student.
- Each column repeats its own question-number labels; do not rely on a single shared numbering axis.
- For the 200-question / two-page layout, repeat the QR code, student info, and corner markers identically on **both** pages — each page is scanned as an independent sheet and merged by `sheet_id`.

### Printing Guidelines
- Print at 100% scale ("Actual Size" / "No Scaling") — browser/printer "fit to page" scaling breaks the bubble-diameter assumptions baked into `SCANNER_BUBBLE_MIN_AREA`/`MAX_AREA`.
- Use plain white paper, 70–90 gsm; avoid glossy stock (glare interferes with adaptive thresholding under phone-camera flash).
- Black-and-white / grayscale printing is sufficient and recommended (color adds no scanning value and increases toner cost).
- Recommended minimum print resolution: 600 DPI for crisp bubble edges.

### Scanner-Friendly Design Rules
1. Never place printed content (logos, decorative lines, watermarks) inside the bubble grid bounding box.
2. Maintain consistent bubble diameter and spacing across every generated sheet for a given exam — mixing bubble sizes mid-sheet is not supported.
3. Keep all four corner markers and the QR code fully within the printable area (some printers clip 3–5mm at the edges — the 10mm outer margin accounts for this).
4. Use pure black (`#000000`) for all structural elements (bubbles, markers, QR code); avoid dark grays, which can fall below the adaptive threshold cutoff under poor lighting.
5. Avoid double-sided printing for single-page layouts — bleed-through can be picked up as false bubble fills on thin paper.

---

## Scanner Workflow

```
1. Teacher opens Scanner page
2. Selects published exam
3. Starts camera (getUserMedia with environment facing)
4. Camera preview shown with scan frame overlay
5. Auto-capture every 3 seconds OR manual capture button

Image Processing Pipeline (Backend):
┌─────────────────────────────────────────────────────┐
│ 1. Decode image bytes → OpenCV numpy array          │
│ 2. Grayscale + Gaussian blur                        │
│ 3. Canny edge detection                             │
│ 4. Find largest 4-sided contour (paper)             │
│ 5. Order corners (TL, TR, BR, BL)                   │
│ 6. Perspective transform → 1200×1600 warped image   │
│ 7. Decode QR code (pyzbar → OpenCV fallback)        │
│ 8. Adaptive threshold for bubble detection          │
│ 9. Find circular contours (area + circularity)      │
│ 10. Organize bubbles into question×option grid      │
│ 11. Calculate fill ratio per bubble                 │
│ 12. Determine student answer (threshold > 0.3)      │
│ 13. Detect multiple marks (warn teacher)            │
│ 14. Compare against answer key                      │
│ 15. Calculate score, percentage, pass/fail          │
│ 16. Return ScanResult with confidence score         │
└─────────────────────────────────────────────────────┘

6. Result displayed instantly with score circle
7. If confidence < threshold → Manual Review mode
8. Teacher can override individual answers
9. Result auto-saved to Firestore
```

### QR Code Data Format
Each answer sheet QR code contains JSON:
```json
{
  "student_id": "firestore_student_id",
  "exam_id": "firestore_exam_id",
  "sheet_id": "exam_id_student_id",
  "class_id": "firestore_class_id",
  "teacher_id": "firebase_uid",
  "version": "1"
}
```

---

## OMR Scanner Technical Design

This section expands the high-level pipeline shown in [Scanner Workflow](#scanner-workflow) into a detailed technical description of each OpenCV stage implemented in `backend/app/scanner/scanner_service.py`.

### Workflow Diagram

```
┌────────────────┐
│ Image Capture   │  Browser getUserMedia() / file upload
└────────┬────────┘
         ▼
┌────────────────┐
│ Image Resize    │  Downscale to IMAGE_MAX_RESOLUTION if larger
└────────┬────────┘
         ▼
┌────────────────┐
│ Grayscale       │  cv2.cvtColor(BGR2GRAY)
│ Conversion      │
└────────┬────────┘
         ▼
┌────────────────┐
│ Gaussian Blur   │  5×5 kernel — suppresses paper-texture noise
└────────┬────────┘
         ▼
┌────────────────┐
│ Edge Detection  │  Canny(50, 150)
└────────┬────────┘
         ▼
┌────────────────┐
│ Paper Detection │  Largest 4-point contour by area
└────────┬────────┘
         ▼
┌────────────────┐
│ Corner Marker   │  Verify/refine using the 4 black corner squares
│ Detection       │  (fallback when the paper-edge contour is weak)
└────────┬────────┘
         ▼
┌────────────────┐
│ Perspective     │  cv2.warpPerspective() → fixed
│ Transform       │  SCANNER_PERSPECTIVE_WIDTH × HEIGHT canvas
└────────┬────────┘
         ▼
┌────────────────┐
│ QR Code         │  pyzbar.decode(); OpenCV QRCodeDetector
│ Detection       │  as fallback if pyzbar finds nothing
└────────┬────────┘
         ▼
┌────────────────┐
│ Adaptive        │  cv2.adaptiveThreshold (Gaussian, block=11, C=2)
│ Threshold       │  on the warped, grayscale image
└────────┬────────┘
         ▼
┌────────────────┐
│ Bubble Grid     │  Find near-circular contours within
│ Detection       │  [BUBBLE_MIN_AREA, BUBBLE_MAX_AREA],
│                 │  cluster into rows (questions) × columns (options)
└────────┬────────┘
         ▼
┌────────────────┐
│ Bubble          │  Map each detected contour to
│ Recognition     │  (question_number, option_letter) via grid position
└────────┬────────┘
         ▼
┌────────────────┐
│ Filled Bubble   │  Compute filled_ratio = dark_pixels / bubble_area
│ Detection       │  within each bubble's masked region
└────────┬────────┘
         ▼
┌────────────────┐
│ Multiple Answer │  Flag question if >1 option has
│ Detection       │  filled_ratio above threshold
└────────┬────────┘
         ▼
┌────────────────┐
│ Confidence      │  Per-question + overall scan_confidence
│ Scoring         │  from fill-ratio separation and QR-decode success
└────────┬────────┘
         ▼
┌────────────────┐
│ Automatic       │  Compare detected answers to answer_key,
│ Grading         │  compute correct/wrong/blank counts, percentage
└────────┬────────┘
         ▼
┌────────────────┐
│ Saving Results  │  If confidence ≥ threshold & AUTO_SAVE_RESULTS:
│                 │  write to Firestore `results` + `scan_history`;
│                 │  otherwise queue for Manual Review
└─────────────────┘
```

### Stage Details

**1. Image Capture** — The frontend camera (`getUserMedia`, environment-facing) or file input captures a JPEG/PNG. Sent to the backend as either multipart file upload (`/scan/process`) or base64 (`/scan/process-base64`, used for live-camera auto-capture).

**2. Image Resize** — Images larger than `IMAGE_MAX_RESOLUTION` are downscaled with `cv2.resize` (`INTER_AREA` interpolation) preserving aspect ratio, bounding processing time regardless of input camera resolution.

**3. Grayscale Conversion** — `cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)`. All downstream geometric detection (paper edges, corner markers, bubbles) operates on intensity only; color is discarded to reduce noise and computation.

**4. Gaussian Blur** — A 5×5 Gaussian kernel smooths high-frequency paper texture and JPEG compression artifacts before edge detection, reducing spurious Canny edges.

**5. Adaptive Threshold** — Applied *after* the perspective warp, not before: `cv2.adaptiveThreshold` with a Gaussian-weighted local neighborhood (block size 11, constant C=2) converts the warped grayscale image into a binary image, compensating for uneven lighting/shadow across the page — a fixed global threshold would fail under phone-camera flash glare or angled lighting.

**6. Edge Detection** — `cv2.Canny(blurred, 50, 150)` on the *original* (unwarped) image to find the paper's outer boundary.

**7. Paper Detection** — `cv2.findContours` on the Canny output; the largest contour that approximates to 4 points (`cv2.approxPolyDP`) is assumed to be the paper boundary.

**8. Perspective Transform** — The 4 corners are ordered (top-left, top-right, bottom-right, bottom-left) and fed into `cv2.getPerspectiveTransform` / `cv2.warpPerspective`, producing a flat, de-skewed image at a fixed canvas size (`SCANNER_PERSPECTIVE_WIDTH` × `SCANNER_PERSPECTIVE_HEIGHT`, default 1200×1600). This fixed canvas is what makes bubble-grid coordinates predictable across every scan.

**9. Corner Marker Detection** — As a robustness check (and fallback when the plain paper-contour approach fails — e.g., photographing on a white desk with low paper/background contrast), the four solid black corner squares defined in the [OMR Answer Sheet Specification](#omr-answer-sheet-specification) are located directly and used to re-derive/verify the warp corners.

**10. QR Code Detection** — `pyzbar.decode()` is tried first (faster, more tolerant of partial damage); if it returns nothing, `cv2.QRCodeDetector().detectAndDecode()` is used as a fallback. The decoded JSON identifies `student_id`, `exam_id`, `class_id`, `teacher_id`, and `sheet_id` without any manual entry.

**11. Bubble Grid Detection** — On the thresholded, warped image, `cv2.findContours` locates all near-circular contours within `[SCANNER_BUBBLE_MIN_AREA, SCANNER_BUBBLE_MAX_AREA]`, filtered by circularity (`4π×area / perimeter²` close to 1.0). Contours are then clustered by Y-coordinate into rows (questions) and by X-coordinate into columns (options A/B/C/D/E), using the known bubble spacing constants from the sheet specification.

**12. Bubble Recognition** — Each grid cell `(row, column)` is mapped to `(question_number, option_letter)` based on its position, independent of contour detection order.

**13. Filled Bubble Detection** — For each bubble, a circular mask is applied to the corresponding region of the warped grayscale image, and `filled_ratio` is computed as the proportion of pixels darker than a local threshold within that mask. An option is considered "marked" when `filled_ratio` exceeds `SCANNER_CONFIDENCE_THRESHOLD`-derived cutoff (default 0.3, per the existing Scanner Workflow documentation).

**14. Multiple Answer Detection** — If more than one option in a question exceeds the fill threshold, the question is flagged `has_multiple_marks = true` and counted separately from both correct and wrong answers (see `multiple_marks_count` in the `results` schema), rather than being silently marked wrong.

**15. Confidence Scoring** — Per-question confidence is derived from the *separation* between the highest and second-highest `filled_ratio` values (a clearly filled bubble vs. clearly empty ones yields high confidence; two similarly-shaded bubbles yield low confidence). The overall `scan_confidence` for the sheet is the weighted average across all questions, adjusted downward if the QR code failed to decode or if the paper-detection contour had low corner-angle confidence.

**16. Automatic Grading** — Detected answers are compared against `exam.answer_key`; `correct_count`, `wrong_count`, `blank_count`, and `multiple_marks_count` are tallied, and `percentage` / `passed` are computed against `exam.passing_score`.

**17. Saving Results** — If `scan_confidence ≥ SCANNER_CONFIDENCE_THRESHOLD` and `AUTO_SAVE_RESULTS=true`, the result is written directly to the `results` collection and mirrored into `scan_history`. Otherwise, it is held in a `pending_review` state (visible under `GET /results/pending-review`) until a teacher confirms or corrects it via `PUT /results/{id}/review`.

---

## Scanner Performance Targets

Measurable targets for the OMR pipeline described above. These are design targets to validate against in the [Testing Plan](#testing-plan) (specifically Scanner Accuracy Testing and Performance Testing), not guaranteed SLAs.

| Metric | Target |
|--------|--------|
| Expected scan speed | 1–2 seconds per sheet on modern server hardware (matches existing Developer Notes); ≤ `SCAN_TIMEOUT` (default 15s) worst case |
| Minimum confidence score for auto-accept | ≥ 0.7 (`SCANNER_CONFIDENCE_THRESHOLD` default) |
| Supported lighting conditions | Indoor ambient light (200–1000 lux); direct camera flash supported via adaptive thresholding; not guaranteed in near-dark conditions (< 50 lux) |
| Supported camera resolution | 5 MP minimum, 12 MP+ recommended (typical modern smartphone rear camera) |
| Recommended phone distance | 20–30 cm above the sheet, sheet filling 80%+ of the frame |
| Maximum paper rotation | ±15° from perfectly aligned before perspective-correction confidence drops significantly; up to ±25° still processable with reduced confidence |
| Expected accuracy | ≥ 98% correct bubble read rate under recommended conditions (good lighting, fully filled bubbles, ≤15° rotation) |
| False positive rate (marking blank as filled) | < 1% under recommended conditions |
| False negative rate (marking filled as blank) | < 2% under recommended conditions, primarily driven by light/incomplete pencil fills |
| Multiple-mark detection rate | ≥ 99% (structural comparison of fill ratios, not affected by lighting as much as single-bubble accuracy) |
| QR decode success rate | ≥ 99.5% under recommended conditions; text-based `sheet_id` footer serves as manual fallback |
| Throughput (batch scanning) | ≥ 30 sheets/minute sustained when scanning a full class sequentially via the camera auto-capture flow |

---

## Deployment Guide

### Backend → Railway

1. Create account at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Set root directory to `backend/`
4. Add environment variables from `.env`
5. Railway auto-detects Python and runs `uvicorn main:app`

**Procfile** (create in backend/):
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend → Vercel

1. Create account at [vercel.com](https://vercel.com)
2. Import GitHub repo
3. Set root directory to `frontend/`
4. No build command needed (static files)
5. Update `APP_CONFIG.apiBase` in all HTML files to your Railway URL

**vercel.json** (create in frontend/):
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/$1" }],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    }
  ]
}
```

### CORS Update
After deployment, update `CORS_ORIGINS` in `.env`:
```
CORS_ORIGINS=["https://your-app.vercel.app"]
```

---

## Logging Strategy

Logging is split by concern into separate rotating log files under `backend/logs/` (see [Expanded Project Structure](#expanded-project-structure)), controlled by the `LOG_LEVEL` environment variable. All logs use the same base format already configured in `main.py`: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`, with each category using a dedicated Python logger name so handlers can be attached per-file.

### Log Categories

| Log | Logger name | File | Captures |
|-----|-------------|------|----------|
| API Logs | `app.api` | `logs/api.log` | Every request: method, path, status code, `X-Process-Time`, teacher UID (if authenticated) |
| Scanner Logs | `app.scanner` | `logs/scanner.log` | Each scan attempt: image size, processing time per stage, confidence score, QR decode success/failure, error reason on failure |
| Authentication Logs | `app.auth` | `logs/auth.log` | Login attempts (success/failure), token refresh, password resets, registration events |
| Error Logs | `app.error` (root exception handler) | `logs/error.log` | All unhandled exceptions caught by the global exception handler in `main.py`, with full stack trace |
| Audit Logs | `app.audit` | `logs/audit.log` | Mutating operations on sensitive resources: exam creation/deletion, result manual overrides, student data import/export, settings changes — includes who, what, and when |

### Log Rotation
- Rotating by size using `logging.handlers.RotatingFileHandler`: 10 MB per file, 5 backups retained per category (`api.log`, `api.log.1` … `api.log.5`).
- Alternative for long-running deployments: `TimedRotatingFileHandler` rotating daily at midnight, retaining 30 days.
- In containerized deployments (Railway/Render), logs should also stream to stdout/stderr so the platform's native log aggregation captures them; file rotation remains as a local backup.

### Example Log Entries

```
2026-07-09 09:12:03,441 - app.auth - INFO - Login success: teacher_id=firebase_uid_8f2a, ip=203.0.113.4
2026-07-09 09:14:47,102 - app.api - INFO - POST /api/v1/exams 201 created in 142.3ms teacher_id=firebase_uid_8f2a
2026-07-09 09:15:02,558 - app.scanner - INFO - Scan processed: exam_id=exam_a1, student_id=std_014, confidence=0.94, time_ms=1180, status=completed
2026-07-09 09:15:33,910 - app.scanner - WARNING - Low confidence scan: exam_id=exam_a1, student_id=std_017, confidence=0.52, reason=qr_decode_failed, queued_for_review=true
2026-07-09 09:20:11,004 - app.audit - INFO - Manual review override: teacher_id=firebase_uid_8f2a, result_id=res_339, question=12, old_answer=C, new_answer=B
2026-07-09 09:31:55,776 - app.error - ERROR - Unhandled exception: FirestoreError('deadline exceeded') at POST /api/v1/students/import [traceback omitted for brevity]
```

---

## Backup and Recovery Plan

### Firestore Backup
- Enable **scheduled exports** via Google Cloud's `gcloud firestore export` (Cloud Scheduler + Cloud Functions, or Firebase's native scheduled backup feature) to a dedicated Cloud Storage bucket, separate from the application's `FIREBASE_STORAGE_BUCKET`.
- Exports are full-database snapshots in Firestore's native export format, restorable via `gcloud firestore import`.
- `scripts/backup_firestore.py` provides a manual on-demand trigger for ad-hoc backups (e.g., immediately before a schema migration).

### Storage Backup
- Firebase Storage (holding scanned answer-sheet images, generated PDFs, and school logos) is backed up via **Cloud Storage bucket-to-bucket replication** or a scheduled `gsutil rsync` job to a secondary bucket/region.
- Scanned images tied to `results` documents are considered semi-permanent evidence and should follow the same retention policy as the `results` collection itself (see Data Retention below).

### Disaster Recovery
1. **Detection:** Uptime monitoring on `/health` (backend) and the frontend's static hosting; alerting on sustained 5xx rates from `error.log` / platform metrics.
2. **Failover:** Backend redeploys are stateless (Railway/Render) — a fresh deploy from the last known-good Git commit restores service; no backend-local state is authoritative.
3. **Data recovery:** If Firestore data is corrupted or lost, restore from the most recent scheduled export (target: ≤ 24 hours of data loss, see Backup Frequency).
4. **Communication:** Maintain a status/incident log for transparency with teachers, particularly around any in-progress scan sessions that may need to be redone.

### Restore Process
1. Identify the target export timestamp in the backup Cloud Storage bucket.
2. If restoring into the same project, first export the *current* (corrupted) state as a safety snapshot.
3. Run `gcloud firestore import gs://<backup-bucket>/<export-timestamp>` — Firestore import overwrites documents with matching IDs and adds new ones; it does not delete documents absent from the import unless explicitly configured.
4. Verify a sample of restored `teachers`, `exams`, and `results` documents against known-good expectations before resuming write traffic.
5. Restore associated Storage objects (scanned images, PDFs) from the Storage backup for the same time window.

### Backup Frequency
| Data | Frequency | Retention |
|------|-----------|-----------|
| Firestore full export | Daily (automated) | 30 daily snapshots, then weekly for 6 months |
| Firestore full export | Before any manual schema migration | Kept indefinitely alongside the migration record |
| Storage bucket replication | Continuous (near real-time) | Matches primary bucket retention |

### Data Retention
- Active teacher accounts: data retained indefinitely while the account is active.
- Deleted/deactivated teacher accounts: soft-deleted (`is_active = false`) for 90 days to allow recovery, then hard-deleted along with associated Storage objects.
- Scan images: retained as long as the associated `result` document exists, to support manual re-review; purged when a result is explicitly deleted.
- Log files: rotated per the [Logging Strategy](#logging-strategy); audit logs retained for a minimum of 1 year for accountability purposes.

---

## Testing Plan

### Unit Testing
- **Scope:** Individual functions in `services/*.py`, `utils/auth.py`, and pure-logic pieces of `scanner_service.py` (e.g., `_order_corners`, fill-ratio math) in isolation, with Firestore and OpenCV I/O mocked.
- **Tooling:** `pytest` + `pytest-mock`, located in `backend/tests/unit/`.
- **Pass/Fail:** 100% of unit tests pass; target ≥ 80% line coverage on `services/` and `utils/`.

### Integration Testing
- **Scope:** Full request/response cycles through FastAPI's `TestClient` against each router in `api/v1/`, using a mocked/emulated Firestore (Firebase Local Emulator Suite recommended).
- **Tooling:** `pytest` + `httpx` + Firebase Emulator, in `backend/tests/integration/`.
- **Pass/Fail:** Every documented endpoint in [API Documentation](#api-documentation) has at least one happy-path and one error-path test; all return the [Standard REST API Response Format](#standard-rest-api-response-format).

### Scanner Accuracy Testing
- **Scope:** Run the full OMR pipeline against a labeled fixture set of real scanned/photographed answer sheets (`backend/tests/fixtures/`) covering: fully filled bubbles, light pencil fills, multiple marks, skewed/rotated photos, poor lighting, and blank sheets.
- **Expected Results:** Detected answers match ground-truth labels at or above the accuracy targets in [Scanner Performance Targets](#scanner-performance-targets).
- **Pass/Fail:** Fails the build if measured accuracy on the fixture set drops below 95% (below the 98% target, with margin) or if any fixture crashes the pipeline instead of returning a graceful error/low-confidence result.

### Authentication Testing
- **Scope:** Registration, login, token refresh, expired/invalid token handling, password reset flow, and Firestore Security Rules (verifying a teacher cannot read/write another teacher's documents).
- **Pass/Fail:** All auth error responses match the codes in [Standard REST API Response Format](#standard-rest-api-response-format); cross-tenant access attempts are rejected with `403`/Security Rules denial in 100% of cases.

### CRUD Testing
- **Scope:** Create/read/update/(soft)delete for every core resource: subjects, classes, students, exams, results, settings.
- **Pass/Fail:** Every CRUD operation returns correct status codes, denormalized counters (e.g., `student_count`, `total_exams`) update correctly, and soft-deleted records are excluded from default list queries.

### Export Testing
- **Scope:** Excel/CSV/PDF generation for reports (`/reports/*`), student import/export, and answer-sheet PDF generation (single and batch).
- **Pass/Fail:** Generated files open without corruption in Excel/Google Sheets/a PDF viewer; exported row counts match source data; batch answer-sheet PDFs contain one correctly-populated sheet per student with a valid, unique QR code.

### Performance Testing
- **Scope:** API response times under normal load; scanner processing time per image; dashboard query times against a Firestore dataset sized to a realistic school (thousands of students/results).
- **Pass/Fail:** P95 API latency (excluding scanner endpoints) < 500ms; scanner P95 < `SCAN_TIMEOUT`; dashboard stat queries < 1s using the documented composite indexes.

### Cross Browser Testing
- **Scope:** Frontend functionality (auth, camera access, dashboard charts, PDF downloads) on latest Chrome, Firefox, Safari, and Edge (desktop).
- **Pass/Fail:** No console errors on load; all pages render and are functional; `getUserMedia` camera access works or degrades gracefully (falls back to file upload) on browsers/contexts where it's unavailable.

### Android Testing
- **Scope:** Scanner camera flow, PWA install prompt, offline behavior (`sw.js`), and responsive layout on representative Android devices/Chrome versions.
- **Pass/Fail:** Camera captures usable images for scanning; PWA installs and launches correctly; core pages remain usable at common Android viewport widths.

### iPhone Testing
- **Scope:** Same as Android, on Safari/iOS — particularly `getUserMedia` behavior (iOS Safari has historically had stricter camera permission/HTTPS requirements) and "Add to Home Screen" PWA behavior.
- **Pass/Fail:** Camera scanning works over HTTPS; layout is usable on standard iPhone viewport widths; no iOS-Safari-specific console errors.

### Tablet Testing
- **Scope:** Layout and scanner usability on iPad and representative Android tablets, where teachers are likely to review results at a larger scan-in-bulk workflow.
- **Pass/Fail:** Dashboard, exam, and scanner pages adapt correctly to tablet breakpoints without horizontal scrolling or overlapping elements.

### Stress Testing
- **Scope:** Concurrent scan submissions (simulating multiple teachers scanning simultaneously), large batch answer-sheet generation (200 students × 200 questions), and sustained API load.
- **Pass/Fail:** No dropped requests or unhandled exceptions under 10x expected concurrent load; graceful `429`/queueing behavior rather than crashes when limits are exceeded.

### Acceptance Testing
- **Scope:** End-to-end scenario walkthroughs with an actual teacher user: create subject → class → import students → create exam with answer key → generate answer sheets → print → scan completed sheets → review results → export report.
- **Expected Results:** The full workflow completes without developer intervention, producing a correct, exportable gradebook.
- **Pass/Fail:** Sign-off from a non-developer test user completing the full scenario unassisted, with zero data-correctness issues found in the exported report.

### Expected Results & Pass/Fail Criteria Summary

| Test Type | Primary Metric | Pass Threshold |
|-----------|-----------------|-----------------|
| Unit | Test pass rate / coverage | 100% pass, ≥ 80% coverage |
| Integration | Endpoint coverage | 100% of documented endpoints tested |
| Scanner Accuracy | Bubble-read accuracy | ≥ 95% on fixture set |
| Authentication | Cross-tenant isolation | 0 unauthorized access successes |
| CRUD | Data integrity after operations | 0 counter/state mismatches |
| Export | File validity | 100% of exports open without corruption |
| Performance | P95 latency | API < 500ms, scanner < `SCAN_TIMEOUT` |
| Cross Browser / Android / iPhone / Tablet | Functional parity | No blocking defects on any target |
| Stress | Error rate under 10x load | No crashes; graceful degradation only |
| Acceptance | End-to-end completion | Full workflow completed with zero data errors |

---

## Developer Notes

### Adding a New Page
1. Create `frontend/pages/new-page.html`
2. Import `requireAuth` and call it at the top of the module script
3. Import and call `renderLayout('Page Title')`
4. Add nav link to `components/layout.js` NAV_ITEMS array

### Adding a New API Endpoint
1. Add route to appropriate `backend/app/api/v1/*.py` file
2. Add corresponding method to `frontend/assets/js/api.js`
3. Add Pydantic schema to `backend/app/schemas/__init__.py` if needed

### Scanner Accuracy Tips
- Ensure good lighting (avoid shadows on bubbles)
- Use black/blue pen for filling bubbles
- Fill bubbles completely and darkly
- Adjust `SCANNER_CONFIDENCE_THRESHOLD` in `.env` (default 0.7)
- Adjust `SCANNER_BUBBLE_MIN_AREA` and `SCANNER_BUBBLE_MAX_AREA` for different paper sizes

### Performance
- Scanner processes in ~1-2 seconds on modern hardware
- Firestore queries use composite indexes for teacher_id + created_at
- Frontend uses debounced search (300ms) to reduce API calls
- Charts use Chart.js with canvas rendering for performance

### Known Limitations
- Firestore does not support full-text search; search is done client-side after fetching
- The `_calculate_fill_ratio` in scanner_service.py uses a simplified area-based approach; for production, pass the warped image to analyze actual pixel darkness
- Batch PDF generation for answer sheets needs a proper PDF merge library (pypdf2/pikepdf) for production

### Environment Variables Reference
| Variable | Description |
|----------|-------------|
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_PRIVATE_KEY` | Service account private key |
| `FIREBASE_CLIENT_EMAIL` | Service account email |
| `JWT_SECRET_KEY` | Secret for signing JWTs (use 32+ random chars) |
| `SCANNER_CONFIDENCE_THRESHOLD` | Min confidence to auto-accept scan (0.0-1.0) |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |
