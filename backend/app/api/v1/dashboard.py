"""
Dashboard API Routes
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta

from app.services.teacher_service import teacher_service
from app.services.exam_service import exam_service
from app.services.result_service import result_service
from app.services.scan_history_service import scan_history_service
from app.services.student_service import student_service
from app.services.class_service import class_service
from app.utils.auth import get_current_user, TokenData
from app.firebase.init_firebase import get_firestore_client, Collections

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(current_user: TokenData = Depends(get_current_user)):
    """Get dashboard statistics"""
    return await teacher_service.get_dashboard_stats(current_user.uid)


@router.get("/charts/score-distribution")
async def get_score_distribution(
    exam_id: Optional[str] = None,
    days: int = 30,
    current_user: TokenData = Depends(get_current_user)
):
    """Get score distribution chart data"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()

    # Build query
    date_from = datetime.utcnow() - timedelta(days=days)
    query = db.collection(Collections.RESULTS).where(
        "teacher_id", "==", current_user.uid
    ).where("created_at", ">=", date_from)

    if exam_id:
        query = query.where("exam_id", "==", exam_id)

    results = query.get()
    scores = [doc.to_dict().get('percentage', 0) for doc in results]

    # Create distribution
    distribution = {
        "0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0
    }
    for score in scores:
        if score <= 20:
            distribution["0-20"] += 1
        elif score <= 40:
            distribution["21-40"] += 1
        elif score <= 60:
            distribution["41-60"] += 1
        elif score <= 80:
            distribution["61-80"] += 1
        else:
            distribution["81-100"] += 1

    return {
        "labels": list(distribution.keys()),
        "data": list(distribution.values())
    }


@router.get("/charts/score-trend")
async def get_score_trend(
    exam_id: Optional[str] = None,
    days: int = 30,
    current_user: TokenData = Depends(get_current_user)
):
    """Get score trend over time"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()

    date_from = datetime.utcnow() - timedelta(days=days)
    query = db.collection(Collections.RESULTS).where(
        "teacher_id", "==", current_user.uid
    ).where("created_at", ">=", date_from).order_by("created_at")

    if exam_id:
        query = query.where("exam_id", "==", exam_id)

    results = query.get()

    # Group by date
    daily_scores = {}
    for doc in results:
        data = doc.to_dict()
        date_str = data.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')
        if date_str not in daily_scores:
            daily_scores[date_str] = []
        daily_scores[date_str].append(data.get('percentage', 0))

    # Calculate daily averages
    labels = sorted(daily_scores.keys())
    data = [round(sum(daily_scores[d]) / len(daily_scores[d]), 2) for d in labels]

    return {"labels": labels, "data": data}


@router.get("/charts/passing-rate")
async def get_passing_rate_trend(
    exam_id: Optional[str] = None,
    days: int = 30,
    current_user: TokenData = Depends(get_current_user)
):
    """Get passing rate trend"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()

    date_from = datetime.utcnow() - timedelta(days=days)
    query = db.collection(Collections.RESULTS).where(
        "teacher_id", "==", current_user.uid
    ).where("created_at", ">=", date_from).order_by("created_at")

    if exam_id:
        query = query.where("exam_id", "==", exam_id)

    results = query.get()

    # Group by date
    daily_stats = {}
    for doc in results:
        data = doc.to_dict()
        date_str = data.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')
        if date_str not in daily_stats:
            daily_stats[date_str] = {"total": 0, "passed": 0}
        daily_stats[date_str]["total"] += 1
        if data.get('passed', False):
            daily_stats[date_str]["passed"] += 1

    labels = sorted(daily_stats.keys())
    data = [
        round((daily_stats[d]["passed"] / daily_stats[d]["total"]) * 100, 2)
        if daily_stats[d]["total"] > 0 else 0
        for d in labels
    ]

    return {"labels": labels, "data": data}


@router.get("/charts/class-performance")
async def get_class_performance(
    current_user: TokenData = Depends(get_current_user)
):
    """Get performance by class"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()

    classes = db.collection(Collections.CLASSES).where(
        "teacher_id", "==", current_user.uid
    ).where("is_active", "==", True).get()

    class_data = []
    for class_doc in classes:
        class_info = class_doc.to_dict()
        class_info['id'] = class_doc.id

        # Get results for this class
        results = db.collection(Collections.RESULTS).where(
            "class_id", "==", class_info['id']
        ).get()

        scores = [r.to_dict().get('percentage', 0) for r in results]
        if scores:
            class_data.append({
                "class_name": f"{class_info.get('name', '')} {class_info.get('section', '')}",
                "average_score": round(sum(scores) / len(scores), 2),
                "student_count": len(scores),
                "passing_rate": round((sum(1 for s in scores if s >= 60) / len(scores)) * 100, 2)
            })

    return class_data


@router.get("/charts/subject-performance")
async def get_subject_performance(
    current_user: TokenData = Depends(get_current_user)
):
    """Get performance by subject"""
    from app.firebase.init_firebase import get_firestore_client
    db = get_firestore_client()

    subjects = db.collection(Collections.SUBJECTS).where(
        "teacher_id", "==", current_user.uid
    ).where("is_active", "==", True).get()

    subject_data = []
    for subj_doc in subjects:
        subj_info = subj_doc.to_dict()
        subj_info['id'] = subj_doc.id

        # Get exams for this subject
        exams = db.collection(Collections.EXAMS).where(
            "subject_id", "==", subj_info['id']
        ).get()

        all_scores = []
        for exam_doc in exams:
            exam_id = exam_doc.id
            results = db.collection(Collections.RESULTS).where(
                "exam_id", "==", exam_id
            ).get()
            scores = [r.to_dict().get('percentage', 0) for r in results]
            all_scores.extend(scores)

        if all_scores:
            subject_data.append({
                "subject_name": subj_info.get('name', ''),
                "subject_code": subj_info.get('code', ''),
                "average_score": round(sum(all_scores) / len(all_scores), 2),
                "exam_count": len(exams),
                "student_count": len(all_scores)
            })

    return subject_data