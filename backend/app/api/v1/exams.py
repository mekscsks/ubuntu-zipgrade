"""
Exams API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List

from app.schemas import (
    ExamResponse, ExamCreate, ExamUpdate, ExamStatus, SuccessResponse
)
from app.services.exam_service import exam_service
from app.services.subject_service import subject_service
from app.services.class_service import class_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()


@router.get("", response_model=List[ExamResponse])
async def list_exams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[ExamStatus] = None,
    subject_id: Optional[str] = None,
    class_id: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """List exams for current teacher"""
    exams, total = await exam_service.get_exams_by_teacher(
        current_user.uid, page, page_size, search, status, subject_id, class_id
    )
    return exams


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_data: ExamCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new exam"""
    exam_data.teacher_id = current_user.uid

    # Verify subject belongs to teacher
    subject = await subject_service.get_by_id(exam_data.subject_id)
    if not subject or subject.teacher_id != current_user.uid:
        raise HTTPException(status_code=400, detail="Invalid subject")

    # Verify class belongs to teacher
    class_obj = await class_service.get_by_id(exam_data.class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=400, detail="Invalid class")

    # Validate answer key length
    if len(exam_data.answer_key) != exam_data.num_questions:
        raise HTTPException(
            status_code=400,
            detail=f"Answer key must have exactly {exam_data.num_questions} answers"
        )

    return await exam_service.create_exam(exam_data)


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get exam by ID with statistics"""
    exam = await exam_service.get_exam_with_stats(exam_id, current_user.uid)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: str,
    update_data: ExamUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Validate answer key if provided
    if update_data.answer_key and update_data.num_questions:
        if len(update_data.answer_key) != update_data.num_questions:
            raise HTTPException(
                status_code=400,
                detail=f"Answer key must have exactly {update_data.num_questions} answers"
            )
    elif update_data.answer_key and exam.num_questions:
        if len(update_data.answer_key) != exam.num_questions:
            raise HTTPException(
                status_code=400,
                detail=f"Answer key must have exactly {exam.num_questions} answers"
            )

    return await exam_service.update(exam_id, update_data)


@router.delete("/{exam_id}", response_model=SuccessResponse)
async def delete_exam(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete (archive) exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")
    await exam_service.update(exam_id, ExamUpdate(status=ExamStatus.ARCHIVED))
    return SuccessResponse(message="Exam archived")


@router.post("/{exam_id}/publish", response_model=ExamResponse)
async def publish_exam(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Publish exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")
    return await exam_service.publish_exam(exam_id, current_user.uid)


@router.post("/{exam_id}/archive", response_model=ExamResponse)
async def archive_exam(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Archive exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")
    return await exam_service.archive_exam(exam_id, current_user.uid)


@router.post("/{exam_id}/duplicate", response_model=ExamResponse)
async def duplicate_exam(
    exam_id: str,
    new_title: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Duplicate exam"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")
    return await exam_service.duplicate_exam(exam_id, current_user.uid, new_title)


@router.get("/{exam_id}/answer-sheet")
async def generate_answer_sheet(
    exam_id: str,
    student_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Generate printable answer sheet for a student"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    from app.services.student_service import student_service
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")

    from app.scanner.scanner_service import AnswerSheetGenerator, QRCodeData
    generator = AnswerSheetGenerator()

    qr_data = QRCodeData(
        student_id=student.id,
        exam_id=exam.id,
        sheet_id=f"{exam.id}_{student.id}",
        class_id=student.class_id,
        teacher_id=current_user.uid
    )

    from app.services.teacher_service import teacher_service
    teacher = await teacher_service.get_by_uid(current_user.uid)

    pdf_bytes = generator.generate_answer_sheet(
        exam_title=exam.title,
        student_name=f"{student.first_name} {student.last_name}",
        student_id=student.student_number,
        qr_data=qr_data,
        num_questions=exam.num_questions,
        school_name=teacher.school_name if teacher else "School Name",
        paper_size=exam.paper_size.value
    )

    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=answer_sheet_{exam.id}_{student.id}.pdf"}
    )


@router.get("/{exam_id}/answer-sheets/batch")
async def generate_batch_answer_sheets(
    exam_id: str,
    class_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Generate answer sheets for all students in a class"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    from app.services.student_service import student_service
    students, _ = await student_service.get_students_by_class(class_id, page_size=1000)

    if not students:
        raise HTTPException(status_code=404, detail="No students found in class")

    from app.scanner.scanner_service import AnswerSheetGenerator, QRCodeData
    from app.services.teacher_service import teacher_service
    from pypdf import PdfWriter, PdfReader
    import io

    teacher = await teacher_service.get_by_uid(current_user.uid)
    generator = AnswerSheetGenerator()
    writer = PdfWriter()

    for student in students:
        qr_data = QRCodeData(
            student_id=student.id,
            exam_id=exam.id,
            sheet_id=f"{exam.id}_{student.id}",
            class_id=student.class_id,
            teacher_id=current_user.uid
        )
        pdf_bytes = generator.generate_answer_sheet(
            exam_title=exam.title,
            student_name=f"{student.first_name} {student.last_name}",
            student_id=student.student_number,
            qr_data=qr_data,
            num_questions=exam.num_questions,
            school_name=teacher.school_name if teacher else "School Name",
            paper_size=exam.paper_size.value
        )
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)

    from fastapi.responses import Response
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=answer_sheets_{exam.id}_{class_id}.pdf"}
    )