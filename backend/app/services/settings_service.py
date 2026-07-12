"""
Settings Service
Handles teacher settings operations
"""
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.base_service import BaseService
from app.firebase.init_firebase import Collections
from app.schemas import TeacherSettings, SettingsUpdate


class SettingsService(BaseService[TeacherSettings, SettingsUpdate, SettingsUpdate]):
    """Service for teacher settings"""

    def __init__(self):
        super().__init__(Collections.SETTINGS, TeacherSettings)

    async def search(self, query: str, **kwargs):
        """Search settings (not applicable)"""
        return []

    async def get_settings(self, teacher_id: str) -> TeacherSettings:
        """Get teacher settings"""
        doc = self.collection.document(teacher_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return TeacherSettings(**data)
        # Return defaults
        return TeacherSettings()

    async def update_settings(self, teacher_id: str, settings: SettingsUpdate) -> TeacherSettings:
        """Update teacher settings"""
        data = settings.model_dump(exclude_unset=True)
        data['updated_at'] = datetime.utcnow()

        doc_ref = self.collection.document(teacher_id)
        doc_ref.set(data, merge=True)

        doc = doc_ref.get()
        data = doc.to_dict()
        data['id'] = doc.id
        return TeacherSettings(**data)

    async def reset_settings(self, teacher_id: str) -> TeacherSettings:
        """Reset settings to defaults"""
        defaults = TeacherSettings().model_dump()
        defaults['updated_at'] = datetime.utcnow()

        self.collection.document(teacher_id).set(defaults)
        return TeacherSettings(**defaults)


settings_service = SettingsService()