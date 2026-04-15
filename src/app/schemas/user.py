"""
User Create Schema

Schema for creating new users.
"""

from pydantic import EmailStr, Field

from src.app.schemas.base import BaseSchema, TimestampMixin


class UserBase(BaseSchema):
    """Base schema for user"""

    username: str = Field(..., description="Username", min_length=3, max_length=50)
    email: EmailStr = Field(..., description="Email address")
    full_name: str | None = Field(None, description="Full name", max_length=100)


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., description="Password", min_length=8)


class UserResponse(UserBase, TimestampMixin):
    """Schema for user response"""

    id: int = Field(..., description="User ID")
    is_active: bool = Field(..., description="Is user active")
    is_superuser: bool = Field(..., description="Is user superuser")


class UserUpdate(UserBase):
    """Schema for updating a user"""

    username: str | None = Field(
        None, description="Username", min_length=3, max_length=50
    )
    email: EmailStr | None = Field(None, description="Email address")
    full_name: str | None = Field(None, description="Full name", max_length=100)
    is_active: bool | None = Field(None, description="Is user active")
