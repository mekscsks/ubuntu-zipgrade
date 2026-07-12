"""
Base Service Class
Provides common CRUD operations for all services
"""
from typing import Optional, List, Dict, Any, TypeVar, Generic, Type
from datetime import datetime
from abc import ABC, abstractmethod

from google.cloud.firestore import Client, Query, DocumentReference, DocumentSnapshot
from google.cloud.firestore_v1.base_query import FieldFilter

from app.firebase.init_firebase import get_firestore_client, Collections
from app.schemas import IDMixin, TimestampMixin


T = TypeVar('T', bound=IDMixin)
CreateSchema = TypeVar('CreateSchema')
UpdateSchema = TypeVar('UpdateSchema')


class BaseService(Generic[T, CreateSchema, UpdateSchema], ABC):
    """Base service with common CRUD operations"""

    def __init__(self, collection_name: str, model_class: Type[T]):
        self.collection_name = collection_name
        self.model_class = model_class
        self._db: Optional[Client] = None

    @property
    def db(self) -> Client:
        if self._db is None:
            self._db = get_firestore_client()
        return self._db

    @property
    def collection(self):
        return self.db.collection(self.collection_name)

    def _doc_to_model(self, doc: DocumentSnapshot) -> Optional[T]:
        """Convert Firestore document to model"""
        if not doc.exists:
            return None
        data = doc.to_dict()
        data['id'] = doc.id
        return self.model_class(**data)

    def _prepare_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for creation"""
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        return data

    def _prepare_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for update"""
        data['updated_at'] = datetime.utcnow()
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    async def create(self, data, doc_id: Optional[str] = None) -> T:
        """Create a new document"""
        if hasattr(data, 'model_dump'):
            create_data = self._prepare_create_data(data.model_dump(exclude_unset=True))
        else:
            create_data = self._prepare_create_data(dict(data))
        if doc_id:
            doc_ref = self.collection.document(doc_id)
            doc_ref.set(create_data)
            return self._doc_to_model(doc_ref.get())
        else:
            doc_ref = self.collection.document()
            doc_ref.set(create_data)
            return self._doc_to_model(doc_ref.get())

    async def get_by_id(self, doc_id: str) -> Optional[T]:
        """Get document by ID"""
        doc = self.collection.document(doc_id).get()
        return self._doc_to_model(doc)

    async def get_all(
        self,
        filters: Optional[List[tuple]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "ASCENDING",
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[T]:
        """Get all documents with optional filters, ordering, and pagination"""
        query: Query = self.collection

        if filters:
            for field, op, value in filters:
                query = query.where(filter=FieldFilter(field, op, value))

        if order_by:
            direction = Query.DESCENDING if order_direction == "DESCENDING" else Query.ASCENDING
            query = query.order_by(order_by, direction=direction)

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        docs = query.get()
        return [self._doc_to_model(doc) for doc in docs if doc.exists]

    async def update(self, doc_id: str, data) -> Optional[T]:
        """Update document"""
        if hasattr(data, 'model_dump'):
            update_data = self._prepare_update_data(data.model_dump(exclude_unset=True))
        else:
            update_data = self._prepare_update_data(dict(data) if not isinstance(data, dict) else data)
        if not update_data:
            return await self.get_by_id(doc_id)

        doc_ref = self.collection.document(doc_id)
        doc_ref.update(update_data)
        return self._doc_to_model(doc_ref.get())

    async def delete(self, doc_id: str) -> bool:
        """Delete document"""
        try:
            self.collection.document(doc_id).delete()
            return True
        except Exception:
            return False

    async def count(self, filters: Optional[List[tuple]] = None) -> int:
        """Count documents with optional filters"""
        query: Query = self.collection

        if filters:
            for field, op, value in filters:
                query = query.where(filter=FieldFilter(field, op, value))

        # Use aggregation query for counting
        try:
            count_query = query.count()
            result = count_query.get()
            return result[0][0].value
        except Exception:
            # Fallback: fetch all and count (less efficient)
            docs = query.get()
            return len(docs)

    async def exists(self, doc_id: str) -> bool:
        """Check if document exists"""
        doc = self.collection.document(doc_id).get()
        return doc.exists

    async def query_one(self, filters: List[tuple]) -> Optional[T]:
        """Query single document matching filters"""
        query: Query = self.collection
        for field, op, value in filters:
            query = query.where(filter=FieldFilter(field, op, value))
        query = query.limit(1)
        docs = query.get()
        return self._doc_to_model(docs[0]) if docs else None

    async def batch_create(self, items: List[CreateSchema]) -> List[T]:
        """Create multiple documents in batch"""
        batch = self.db.batch()
        results = []

        for item in items:
            doc_ref = self.collection.document()
            create_data = self._prepare_create_data(item.model_dump(exclude_unset=True))
            batch.set(doc_ref, create_data)
            # We'll need to fetch after commit
            results.append((doc_ref, item))

        batch.commit()

        # Fetch created documents
        created = []
        for doc_ref, _ in results:
            doc = doc_ref.get()
            created.append(self._doc_to_model(doc))

        return created

    async def batch_update(self, updates: List[tuple[str, UpdateSchema]]) -> List[T]:
        """Update multiple documents in batch"""
        batch = self.db.batch()

        for doc_id, data in updates:
            update_data = self._prepare_update_data(data.model_dump(exclude_unset=True))
            if update_data:
                doc_ref = self.collection.document(doc_id)
                batch.update(doc_ref, update_data)

        batch.commit()

        # Fetch updated documents
        updated = []
        for doc_id, _ in updates:
            doc = self.collection.document(doc_id).get()
            updated.append(self._doc_to_model(doc))

        return updated

    async def batch_delete(self, doc_ids: List[str]) -> int:
        """Delete multiple documents in batch"""
        batch = self.db.batch()
        for doc_id in doc_ids:
            doc_ref = self.collection.document(doc_id)
            batch.delete(doc_ref)
        batch.commit()
        return len(doc_ids)

    # Abstract methods for service-specific logic
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[T]:
        """Search documents"""
        pass