"""
Base Schema

Contains base schema classes with common functionality.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    class Config:
        from_attributes = True


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class MessageResponse(BaseModel):
    """Generic message response"""

    message: str = Field(..., description="Response message")


class StatusResponse(BaseModel):
    """Generic status response"""

    status: str = Field(..., description="Status")
    message: str | None = Field(None, description="Optional message")


class PaginatedResponse(BaseModel):
    """Generic paginated response"""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
