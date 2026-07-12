"""
Scan History Service
Handles scan history/log operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import ScanHistoryResponse, ScanHistoryCreate, ScanStatus


class ScanHistoryService(BaseService[ScanHistoryResponse, ScanHistoryCreate, ScanHistoryCreate]):
    """Service for scan history operations"""

    def __init__(self):
        super().__init__(Collections.SCAN_HISTORY, ScanHistoryResponse)

    async def create_scan_log(self, scan_data: ScanHistoryCreate) -> ScanHistoryResponse:
        """Create a new scan history entry"""
        data = scan_data.model_dump()
        data['created_at'] = datetime.utcnow()
        return await self.create(data)

    async def get_scan_history_by_teacher(
        self,
        teacher_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ScanStatus] = None,
        exam_id: Optional[str] = None,
        student_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> tuple[List[ScanHistoryResponse], int]:
        """Get scan history for a teacher with filters"""
        filters = [("teacher_id", "==", teacher_id)]
        if status:
            filters.append(("status", "==", status.value))
        if exam_id:
            filters.append(("exam_id", "==", exam_id))
        if student_id:
            filters.append(("student_id", "==", student_id))
        if date_from:
            filters.append(("created_at", ">=", date_from))
        if date_to:
            filters.append(("created_at", "<=", date_to))

        history = await self.get_all(
            filters=filters,
            order_by="created_at",
            order_direction="DESCENDING",
            limit=page_size,
            offset=(page - 1) * page_size
        )
        total = await self.count(filters)
        return history, total

    async def get_scan_history_by_exam(self, exam_id: str) -> List[ScanHistoryResponse]:
        """Get scan history for an exam"""
        filters = [("exam_id", "==", exam_id)]
        return await self.get_all(filters=filters, order_by="created_at", order_direction="DESCENDING")

    async def update_scan_status(
        self,
        scan_id: str,
        status: ScanStatus,
        result_id: Optional[str] = None,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> Optional[ScanHistoryResponse]:
        """Update scan status"""
        update_data = {"status": status.value}
        if result_id:
            update_data["result_id"] = result_id
        if error_message:
            update_data["error_message"] = error_message
        if processing_time_ms:
            update_data["processing_time_ms"] = processing_time_ms
        return await self.update(scan_id, update_data)

    async def get_recent_scans(self, teacher_id: str, limit: int = 10) -> List[ScanHistoryResponse]:
        """Get recent scans for dashboard"""
        filters = [("teacher_id", "==", teacher_id)]
        return await self.get_all(filters=filters, order_by="created_at", order_direction="DESCENDING", limit=limit)

    async def get_scans_today_count(self, teacher_id: str) -> int:
        """Get count of scans today"""
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        filters = [
            ("teacher_id", "==", teacher_id),
            ("created_at", ">=", today_start)
        ]
        return await self.count(filters)

    async def search(self, query: str, **kwargs) -> List[ScanHistoryResponse]:
        """Search scan history"""
        all_history = await self.get_all()
        q = query.lower()
        return [h for h in all_history if q in (h.student_name or "").lower()]

    async def get_failed_scans(self, teacher_id: str, limit: int = 50) -> List[ScanHistoryResponse]:
        """Get failed scans for review"""
        filters = [
            ("teacher_id", "==", teacher_id),
            ("status", "==", ScanStatus.FAILED.value)
        ]
        return await self.get_all(filters=filters, order_by="created_at", order_direction="DESCENDING", limit=limit)


scan_history_service = ScanHistoryService()