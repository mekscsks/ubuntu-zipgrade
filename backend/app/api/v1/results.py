"""
Results API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime

from app.schemas import (
    ScanResultResponse, QuestionResult, SuccessResponse, ScanStatus
)
from app.services.result_service import result_service
from app.services.exam_service import exam_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()


@router.get("/exam/{exam_id}", response_model=List[ScanResultResponse])
async def get_exam_results(
    exam_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user)
):
    """Get all results for an exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    results = await result_service.get_results_by_exam(exam_id)
    # Paginate manually
    offset = (page - 1) * page_size
    return results[offset:offset + page_size]


@router.get("/exam/{exam_id}/statistics")
async def get_exam_statistics(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get statistics for an exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    return await result_service.get_exam_statistics(exam_id)


@router.get("/student/{student_id}", response_model=List[ScanResultResponse])
async def get_student_results(
    student_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all results for a student"""
    from app.services.student_service import student_service
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")

    return await result_service.get_results_by_student(student_id)


@router.get("/student/{student_id}/exam/{exam_id}", response_model=ScanResultResponse)
async def get_student_exam_result(
    student_id: str,
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific student's result for an exam"""
    from app.services.student_service import student_service
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")

    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    result = await result_service.get_student_exam_result(student_id, exam_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.get("/pending-review", response_model=List[ScanResultResponse])
async def get_pending_review(
    current_user: TokenData = Depends(get_current_user)
):
    """Get results pending manual review"""
    return await result_service.get_results_pending_review(current_user.uid)


@router.put("/{result_id}/review", response_model=ScanResultResponse)
async def review_result(
    result_id: str,
    question_results: List[QuestionResult],
    review_notes: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Update result after manual review"""
    result = await result_service.get_by_id(result_id)
    if not result or result.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Result not found")

    updated = await result_service.update_result_review(
        result_id, question_results, review_notes
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update result")
    return updated


@router.delete("/exam/{exam_id}", response_model=SuccessResponse)
async def delete_exam_results(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete all results for an exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    count = await result_service.delete_results_by_exam(exam_id)
    return SuccessResponse(message=f"Deleted {count} results")