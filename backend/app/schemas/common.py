from datetime import datetime
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class HealthResponse(BaseModel):
    status: str
    uptime: float
    version: str

class StatusResponse(BaseModel):
    status: str
    detail: str

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime
