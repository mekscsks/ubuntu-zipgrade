"""
API v1 Router
"""
from fastapi import APIRouter

from app.api.v1 import auth, teachers, subjects, classes, students, exams, scanner, results, dashboard, settings, reports

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(teachers.router, prefix="/teachers", tags=["Teachers"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(classes.router, prefix="/classes", tags=["Classes"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(exams.router, prefix="/exams", tags=["Exams"])
api_router.include_router(scanner.router, prefix="/scan", tags=["Scanner"])
api_router.include_router(results.router, prefix="/results", tags=["Results"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])