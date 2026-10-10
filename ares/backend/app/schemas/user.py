"""User, Role, and Permission Schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class PermissionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    display_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    roles: List[str] = []
    permissions: List[str] = []

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None
