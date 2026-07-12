"""
Reports API Routes - Export exam results in Excel, CSV, PDF
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Optional, List
from datetime import datetime
import io
import logging

from app.schemas import ReportExportRequest, SuccessResponse
from app.services.result_service import result_service
from app.services.exam_service import exam_service
from app.services.student_service import student_service
from app.services.class_service import class_service
from app.utils.auth import get_current_user, TokenData

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/exam/{exam_id}/excel")
async def export_exam_results_excel(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export exam results as Excel"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    results = await result_service.get_results_by_exam(exam_id)
    data = await _build_results_dataframe(results, exam)

    import pandas as pd
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            "Metric": ["Exam Title", "Total Students", "Average Score", "Highest Score", "Lowest Score", "Passing Rate"],
            "Value": [
                exam.title,
                len(results),
                f"{round(sum(r.percentage for r in results) / len(results), 2)}%" if results else "N/A",
                f"{max(r.percentage for r in results)}%" if results else "N/A",
                f"{min(r.percentage for r in results)}%" if results else "N/A",
                f"{round(sum(1 for r in results if r.passed) / len(results) * 100, 2)}%" if results else "N/A",
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame(data).to_excel(writer, sheet_name="Results", index=False)

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_results.xlsx"}
    )


@router.get("/exam/{exam_id}/csv")
async def export_exam_results_csv(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export exam results as CSV"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    results = await result_service.get_results_by_exam(exam_id)
    data = await _build_results_dataframe(results, exam)

    import pandas as pd
    output = io.StringIO()
    pd.DataFrame(data).to_csv(output, index=False)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_results.csv"}
    )


@router.get("/exam/{exam_id}/pdf")
async def export_exam_results_pdf(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export exam results as PDF"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    results = await result_service.get_results_by_exam(exam_id)
    stats = await result_service.get_exam_statistics(exam_id)

    pdf_bytes = _generate_exam_pdf(exam, results, stats)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_report.pdf"}
    )


@router.get("/student/{student_id}/excel")
async def export_student_report_excel(
    student_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export individual student report as Excel"""
    student = await student_service.get_by_id(student_id)
    if not student or student.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Student not found")

    results = await result_service.get_results_by_student(student_id)

    import pandas as pd
    data = []
    for r in results:
        exam = await exam_service.get_by_id(r.exam_id)
        data.append({
            "Exam": exam.title if exam else r.exam_id,
            "Date": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
            "Score": f"{r.percentage}%",
            "Correct": r.correct_count,
            "Wrong": r.wrong_count,
            "Blank": r.blank_count,
            "Status": "PASSED" if r.passed else "FAILED",
        })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name="Exam History", index=False)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=student_{student_id}_report.xlsx"}
    )


@router.get("/class/{class_id}/excel")
async def export_class_report_excel(
    class_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export class report as Excel"""
    class_obj = await class_service.get_by_id(class_id)
    if not class_obj or class_obj.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Class not found")

    students, _ = await student_service.get_students_by_class(class_id, page_size=1000)

    import pandas as pd
    data = []
    for s in students:
        s_results = await result_service.get_results_by_student(s.id)
        scores = [r.percentage for r in s_results]
        data.append({
            "Student Number": s.student_number,
            "Name": f"{s.first_name} {s.last_name}",
            "Section": s.section or "",
            "Exams Taken": len(s_results),
            "Average Score": f"{round(sum(scores)/len(scores), 2)}%" if scores else "N/A",
            "Highest Score": f"{max(scores)}%" if scores else "N/A",
            "Lowest Score": f"{min(scores)}%" if scores else "N/A",
            "Passing Rate": f"{round(sum(1 for r in s_results if r.passed)/len(s_results)*100, 2)}%" if s_results else "N/A",
        })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name="Class Report", index=False)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=class_{class_id}_report.xlsx"}
    )


@router.get("/exam/{exam_id}/question-analysis/excel")
async def export_question_analysis_excel(
    exam_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Export question analysis as Excel"""
    exam = await exam_service.get_by_id(exam_id)
    if not exam or exam.teacher_id != current_user.uid:
        raise HTTPException(status_code=404, detail="Exam not found")

    stats = await result_service.get_exam_statistics(exam_id)

    import pandas as pd
    data = []
    for qa in stats.get("question_analysis", []):
        data.append({
            "Question #": qa["question_number"],
            "Correct Answer": exam.answer_key[qa["question_number"] - 1] if qa["question_number"] <= len(exam.answer_key) else "",
            "Correct": qa["correct_count"],
            "Wrong": qa["wrong_count"],
            "Blank": qa["blank_count"],
            "Multiple Marks": qa["multiple_marks_count"],
            "Difficulty Index": qa["difficulty_index"],
            "A": qa["option_distribution"].get("A", 0),
            "B": qa["option_distribution"].get("B", 0),
            "C": qa["option_distribution"].get("C", 0),
            "D": qa["option_distribution"].get("D", 0),
            "E": qa["option_distribution"].get("E", 0),
        })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name="Question Analysis", index=False)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_question_analysis.xlsx"}
    )


async def _build_results_dataframe(results, exam) -> list:
    """Build results data for export"""
    data = []
    for r in results:
        s = await student_service.get_by_id(r.student_id)
        data.append({
            "Student Number": s.student_number if s else r.student_id,
            "Student Name": f"{s.first_name} {s.last_name}" if s else "",
            "Section": s.section if s else "",
            "Score (%)": r.percentage,
            "Correct": r.correct_count,
            "Wrong": r.wrong_count,
            "Blank": r.blank_count,
            "Multiple Marks": r.multiple_marks_count,
            "Status": "PASSED" if r.passed else "FAILED",
            "Scan Date": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            "Reviewed": "Yes" if r.reviewed_by_teacher else "No",
        })
    return data


def _generate_exam_pdf(exam, results, stats) -> bytes:
    """Generate PDF report for exam"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=12)
    story.append(Paragraph(f"Exam Report: {exam.title}", title_style))
    story.append(Spacer(1, 0.5*cm))

    # Summary table
    summary_data = [
        ["Metric", "Value"],
        ["Total Students Scanned", str(stats.get("total", 0))],
        ["Average Score", f"{stats.get('average_score', 0)}%"],
        ["Highest Score", f"{stats.get('highest_score', 0)}%"],
        ["Lowest Score", f"{stats.get('lowest_score', 0)}%"],
        ["Passing Rate", f"{stats.get('passing_rate', 0)}%"],
    ]
    t = Table(summary_data, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 1*cm))

    # Results table
    if results:
        story.append(Paragraph("Student Results", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))
        results_data = [["Student ID", "Score", "Correct", "Wrong", "Blank", "Status"]]
        for r in results[:50]:  # Limit to 50 rows in PDF
            results_data.append([
                r.student_id[:12],
                f"{r.percentage}%",
                str(r.correct_count),
                str(r.wrong_count),
                str(r.blank_count),
                "PASSED" if r.passed else "FAILED",
            ])
        t2 = Table(results_data, colWidths=[4*cm, 3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E40AF')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EFF6FF')]),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t2)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
