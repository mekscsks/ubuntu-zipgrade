"""
Scanner API Routes
Handles answer sheet scanning and processing
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from typing import Optional
import base64

from app.schemas import (
    ScanResultResponse, ScanHistoryResponse, SuccessResponse
)
from app.services.exam_service import exam_service
from app.services.result_service import result_service
from app.services.scan_history_service import scan_history_service
from app.services.student_service import student_service
from app.scanner.scanner_service import scanner, ScanResult
from app.utils.auth import get_current_user, TokenData
from app.firebase.init_firebase import get_storage_bucket
from app.config import settings

router = APIRouter()


@router.post("/process", response_model=ScanResultResponse)
async def process_answer_sheet(
    exam_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Process an uploaded answer sheet image
    """
    # Verify exam belongs to teacher
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.status.value != "published":
        raise HTTPException(status_code=400, detail="Exam is not published")

    # Read image
    image_data = await file.read()

    # Validate file size
    if len(image_data) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="File too large")

    # Validate file type
    content_type = file.content_type
    if content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Use JPEG or PNG")

    # Create scan history entry
    from app.schemas import ScanHistoryCreate, ScanStatus
    scan_log = ScanHistoryCreate(
        exam_id=exam_id,
        student_id="",  # Will be filled after QR detection
        class_id=exam.class_id,
        teacher_id=current_user.uid,
        sheet_id="",
        status=ScanStatus.PROCESSING
    )
    history = await scan_history_service.create_scan_log(scan_log)

    try:
        # Process image
        result = scanner.process_image(
            image_data=image_data,
            answer_key=exam.answer_key,
            num_questions=exam.num_questions,
            passing_score=exam.passing_score,
            options_per_question=5 if 'E' in exam.answer_key else 4
        )

        # Update scan history with results
        if result.student_id:
            await scan_history_service.update_scan_status(
                history.id,
                ScanStatus.COMPLETED if result.status == ScanStatus.COMPLETED else ScanStatus.MANUAL_REVIEW,
                result_id=result.id if hasattr(result, 'id') else None,
                processing_time_ms=result.processing_time_ms
            )

            # Update student info in history
            student = await student_service.get_by_id(result.student_id)
            if student:
                from app.firebase.init_firebase import get_firestore_client
                db = get_firestore_client()
                db.collection("scan_history").document(history.id).update({
                    "student_id": result.student_id,
                    "sheet_id": result.sheet_id or ""
                })
        else:
            await scan_history_service.update_scan_status(
                history.id,
                ScanStatus.MANUAL_REVIEW,
                error_message="QR code not detected",
                processing_time_ms=result.processing_time_ms
            )

        # Save result if student identified
        if result.student_id:
            from app.schemas import ScanResultCreate
            result_data = ScanResultCreate(
                exam_id=exam_id,
                student_id=result.student_id,
                class_id=result.class_id or exam.class_id,
                teacher_id=current_user.uid,
                sheet_id=result.sheet_id or f"{exam_id}_{result.student_id}",
                total_questions=result.total_questions,
                correct_count=result.correct_count,
                wrong_count=result.wrong_count,
                blank_count=result.blank_count,
                multiple_marks_count=result.multiple_marks_count,
                percentage=result.percentage,
                passed=result.passed,
                question_results=result.question_results,
                scan_confidence=result.scan_confidence,
                processing_time_ms=result.processing_time_ms,
                status=result.status,
                image_url=None  # Could upload to Firebase Storage
            )
            saved_result = await result_service.create_result(result_data)
            result.id = saved_result.id

            # Increment exam scan count
            await exam_service.increment_scan_count(exam_id)
            # Update exam stats
            await exam_service.update_exam_stats(exam_id)

        return ScanResultResponse(
            **result.__dict__,
            id=result.id if hasattr(result, 'id') else "",
            created_at=None,  # Will be set by Firestore
            updated_at=None
        )

    except Exception as e:
        await scan_history_service.update_scan_status(
            history.id,
            ScanStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Scanning failed: {str(e)}")


@router.post("/process-base64", response_model=ScanResultResponse)
async def process_answer_sheet_base64(
    exam_id: str,
    image_base64: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Process an answer sheet from base64 encoded image (for mobile camera)
    """
    # Verify exam belongs to teacher
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Decode base64
    try:
        # Remove data URL prefix if present
        if image_base64.startswith('data:image'):
            image_base64 = image_base64.split(',')[1]
        image_data = base64.b64decode(image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    # Create scan history
    from app.schemas import ScanHistoryCreate, ScanStatus
    scan_log = ScanHistoryCreate(
        exam_id=exam_id,
        student_id="",
        class_id=exam.class_id,
        teacher_id=current_user.uid,
        sheet_id="",
        status=ScanStatus.PROCESSING
    )
    history = await scan_history_service.create_scan_log(scan_log)

    try:
        # Process image
        result = scanner.process_image(
            image_data=image_data,
            answer_key=exam.answer_key,
            num_questions=exam.num_questions,
            passing_score=exam.passing_score,
            options_per_question=5 if 'E' in exam.answer_key else 4
        )

        # Update scan history
        if result.student_id:
            await scan_history_service.update_scan_status(
                history.id,
                ScanStatus.COMPLETED if result.status == ScanStatus.COMPLETED else ScanStatus.MANUAL_REVIEW,
                processing_time_ms=result.processing_time_ms
            )

            student = await student_service.get_by_id(result.student_id)
            if student:
                from app.firebase.init_firebase import get_firestore_client
                db = get_firestore_client()
                db.collection("scan_history").document(history.id).update({
                    "student_id": result.student_id,
                    "sheet_id": result.sheet_id or ""
                })
        else:
            await scan_history_service.update_scan_status(
                history.id,
                ScanStatus.MANUAL_REVIEW,
                error_message="QR code not detected",
                processing_time_ms=result.processing_time_ms
            )

        # Save result
        if result.student_id:
            from app.schemas import ScanResultCreate
            result_data = ScanResultCreate(
                exam_id=exam_id,
                student_id=result.student_id,
                class_id=result.class_id or exam.class_id,
                teacher_id=current_user.uid,
                sheet_id=result.sheet_id or f"{exam_id}_{result.student_id}",
                total_questions=result.total_questions,
                correct_count=result.correct_count,
                wrong_count=result.wrong_count,
                blank_count=result.blank_count,
                multiple_marks_count=result.multiple_marks_count,
                percentage=result.percentage,
                passed=result.passed,
                question_results=result.question_results,
                scan_confidence=result.scan_confidence,
                processing_time_ms=result.processing_time_ms,
                status=result.status
            )
            saved_result = await result_service.create_result(result_data)
            result.id = saved_result.id

            await exam_service.increment_scan_count(exam_id)
            await exam_service.update_exam_stats(exam_id)

        return ScanResultResponse(
            **result.__dict__,
            id=result.id if hasattr(result, 'id') else "",
            created_at=None,
            updated_at=None
        )

    except Exception as e:
        await scan_history_service.update_scan_status(
            history.id,
            ScanStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Scanning failed: {str(e)}")


@router.get("/history", response_model=list[ScanHistoryResponse])
async def get_scan_history(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    exam_id: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Get scan history for current teacher"""
    from app.schemas import ScanStatus
    scan_status = ScanStatus(status) if status else None
    history, total = await scan_history_service.get_scan_history_by_teacher(
        current_user.uid, page, page_size, scan_status, exam_id
    )
    return history


@router.get("/history/{scan_id}", response_model=ScanHistoryResponse)
async def get_scan_detail(
    scan_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get scan history detail"""
    history = await scan_history_service.get_by_id(scan_id)
    if not history or history.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Scan not found")
    return history


@router.delete("/history/{scan_id}", response_model=SuccessResponse)
async def delete_scan_history(
    scan_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete scan history entry"""
    history = await scan_history_service.get_by_id(scan_id)
    if not history or history.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Scan not found")
    await scan_history_service.delete(scan_id)
    return SuccessResponse(message="Scan history deleted")